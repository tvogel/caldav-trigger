#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations
import logging
import json
import operator
import os
from time import sleep
import dotenv
import sys
from typing import Any
import pyqrcode
from tuya_sharing import CustomerDevice, LoginControl, Manager, SharingDeviceListener, SharingTokenListener, logger

EXIT_OK                    = 0
EXIT_SYNTAX_ERROR          = 1
EXIT_AUTHENTICATION_FAILED = 2
EXIT_HOME_MISSING          = 3
EXIT_SCENE_MISSING         = 4
EXIT_TRIGGER_SCENE_FAILED  = 5

URL_PATH           = "apigw.iotbing.com"
CONF_CLIENT_ID     = "HA_3y9q4ak7g4ephrvke"
CONF_SCHEMA        = "haauthorize"
APP_QR_CODE_HEADER = "tuyaSmart--qrLogin/?token="

LOGGER = logging.getLogger(__package__)
# LOGGER.setLevel(logging.DEBUG)

class TokenListener(SharingTokenListener):
    def __init__(self, client: TuyaQrSharing) -> None:
        super().__init__()
        self.client = client

    def update_token(self, new_token_info: dict[str, Any]):
        LOGGER.debug("update token info : %s", new_token_info)
        self.client.set_token_info(new_token_info)

class DeviceListener(SharingDeviceListener):
    def update_device(self, device: CustomerDevice):
        """Update device info.

        Args:
            device(CustomerDevice): updated device info
        """
        print('update:', device.name, json.dumps(device.status, indent=2))

    def add_device(self, device: CustomerDevice):
        """Device Added.

        Args:
            device(CustomerDevice): Device added
        """
        pass

    def remove_device(self, device_id: str):
        """Device removed.

        Args:
            device_id(str): device's id which removed
        """
        pass

class TuyaQrSharing:
    def __init__(self, dotenv_file: str) -> None:
        self.dotenv_file = dotenv_file
        self.user_code = os.environ.get('tuya_qr_sharing_user_code')
        self.username = os.environ.get('tuya_qr_sharing_username')
        self.terminal_id = os.environ.get('tuya_qr_sharing_terminal_id')
        self.endpoint = os.environ.get('tuya_qr_sharing_endpoint')

        self.home_id = os.environ.get('tuya_qr_sharing_home')

        try:
            self.token_info = json.loads(os.environ.get('tuya_qr_sharing_token_info'))
        except TypeError:
            self.token_info = None

    def set_token_info(self, token_info: dict[str, Any]) -> None:
        self.token_info = token_info
        dotenv.set_key(self.dotenv_file, 'tuya_qr_sharing_token_info', json.dumps(token_info))

    def reload_token_info(self) -> None:
        dotenv_values = dotenv.dotenv_values(self.dotenv_file)
        new_token_info = json.loads(dotenv_values['tuya_qr_sharing_token_info'])
        if new_token_info != self.token_info:
            print('Token info changed, reconnecting...')
            self.token_info = new_token_info
            self.connect()

    def logout(self):
        dotenv.unset_key(self.dotenv_file, 'tuya_qr_sharing_token_info')
        dotenv.unset_key(self.dotenv_file, 'tuya_qr_sharing_username')
        dotenv.unset_key(self.dotenv_file, 'tuya_qr_sharing_terminal_id')
        dotenv.unset_key(self.dotenv_file, 'tuya_qr_sharing_endpoint')
        return EXIT_OK

    def login(self):
        if self.token_info:
            print('You are already logged in.')
            return EXIT_OK

        if not self.user_code:
            self.user_code = input('SmartLife user-code from Settings/Account: ')
            dotenv.set_key(self.dotenv_file, 'tuya_qr_sharing_user_code', self.user_code)

        login_control = LoginControl()

        response = login_control.qr_code(CONF_CLIENT_ID, CONF_SCHEMA, self.user_code)

        if not response.get("success", False):
            print('Could not login: %i %s' % (response.get('code'), response.get('msg')), file = sys.stderr)
            return EXIT_AUTHENTICATION_FAILED

        qr_code = response["result"]["qrcode"]

        while True:
            print ('Please scan this in Smart-Life and authorize access:')
            print (pyqrcode.create(APP_QR_CODE_HEADER + qr_code, mode = 'binary').terminal())
            input ('Then, hit ENTER to continue.')

            ret, info = login_control.login_result(qr_code, CONF_CLIENT_ID, self.user_code)
            if not ret:
                print('Not authorized (yet): %i %s' % (info.get('code'), info.get('msg')), file = sys.stderr)
                print('Try again')
                continue

            self.token_info = {
                "t": info.get("t"),
                "uid": info.get("uid"),
                "expire_time": info.get("expire_time"),
                "access_token": info.get("access_token"),
                "refresh_token": info.get("refresh_token"),
            }

            username = info.get('username')
            terminal_id = info.get('terminal_id')
            endpoint = info.get('endpoint')
            dotenv.set_key(self.dotenv_file, 'tuya_qr_sharing_username', username)
            dotenv.set_key(self.dotenv_file, 'tuya_qr_sharing_token_info', json.dumps(self.token_info))
            dotenv.set_key(self.dotenv_file, 'tuya_qr_sharing_terminal_id', terminal_id)
            dotenv.set_key(self.dotenv_file, 'tuya_qr_sharing_endpoint', endpoint)
            break

        print('You are logged in.')
        return EXIT_OK

    def connect(self):
        if not self.token_info:
            print('Please log in first!', file = sys.stderr);
            return EXIT_AUTHENTICATION_FAILED

        self.token_listener = TokenListener(self)
        self.tuya_sharing_manager = Manager(
            CONF_CLIENT_ID,
            self.user_code,
            self.terminal_id,
            self.endpoint,
            self.token_info,
            self.token_listener
        )

        try:
            self.tuya_sharing_manager.update_device_cache()
        except Exception as e:
            print('Cannot access Tuya/Smartlife (%s)' % (e.args), file=sys.stderr)
            return EXIT_AUTHENTICATION_FAILED

        self.tuya_sharing_manager.user_homes.sort(key = operator.attrgetter('name'))

        return EXIT_OK

    def homes(self):
        print('Homes:')
        for home in self.tuya_sharing_manager.user_homes:
            print('%10s: %s' % (home.id, home.name))
        return EXIT_OK

    def scenes(self):
        for home in self.tuya_sharing_manager.user_homes:
            print('Scenes in home %s (%s):' % (home.name, home.id));
            for scene in sorted(self.tuya_sharing_manager.scene_repository.query_scenes([home.id]),
                   key = operator.attrgetter('name')):
                print('    %s: %s' % (scene.scene_id, scene.name));
        return EXIT_OK

    def activate(self, home_id: str, scene_id: str) -> int:
        print(f"Triggering scene {scene_id} in home {home_id}...")
        try:
            response = self.tuya_sharing_manager.scene_repository.trigger_scene(home_id, scene_id)
        except Exception as e:
            print('Error triggering scene (%s)' % (e.args), file=sys.stderr)
            return EXIT_TRIGGER_SCENE_FAILED

        if not response:
            print('Triggering scene reported failure', file=sys.stderr)
            return EXIT_TRIGGER_SCENE_FAILED
        print('tuya_qr_sharing trigger succeeded.')
        return EXIT_OK

    def monitor(self):
        for device in self.tuya_sharing_manager.device_map.values():
            device.set_up = True
            # device.support_local = False
            print(device)

        device_listener = DeviceListener()
        self.tuya_sharing_manager.add_device_listener(device_listener)
        self.tuya_sharing_manager.refresh_mq()

        # handle being interrupted
        try:
            # wait around
            while True:
                print('Main thread waiting...')
                sleep(1)
        except KeyboardInterrupt:
            # terminate main thread
            print('Main interrupted! Exiting.')
            self.tuya_sharing_manager.mq.stop()
            return EXIT_OK

    def activate_from_env(self, variable: str) -> int:
        if not self.home_id:
            print('Set tuya_qr_sharing_home in .env first, in order to trigger scenes!', file=sys.stderr)
            return EXIT_HOME_MISSING

        if not (scene_id := os.environ.get(variable)):
            print(f'Set {variable} in .env first!', file=sys.stderr)
            return EXIT_SCENE_MISSING

        return self.activate(self.home_id, scene_id)

    def on(self):
        return self.activate_from_env('tuya_qr_sharing_scene_on')

    def off(self):
        return self.activate_from_env('tuya_qr_sharing_scene_off')

def main() -> int:

    logger.setLevel(LOGGER.getEffectiveLevel())

    dotenv_file = dotenv.find_dotenv(usecwd=True) or dotenv.find_dotenv()
    dotenv.load_dotenv(dotenv_file)

    try:
        cmd = sys.argv[1]
    except IndexError:
        cmd = ''

    cmds = [ 'login', 'logout', 'homes', 'scenes', 'on', 'off', 'monitor', 'activate' ]
    if not cmd in cmds:
        print('Syntax: tuya-qr-sharing.py (%s)' % '|'.join(cmds), file=sys.stderr)
        return EXIT_SYNTAX_ERROR;

    client = TuyaQrSharing(dotenv_file)

    if cmd == 'logout':
        return client.logout()

    if cmd == 'login':
        return client.login()

    if (result := client.connect()) != EXIT_OK:
        return result

    if cmd == 'homes':
        return client.homes()

    if cmd == 'scenes':
        return client.scenes()

    if cmd == 'activate':
        try:
            home_id = sys.argv[2]
            scene_id = sys.argv[3]
        except IndexError:
            print('Syntax: tuya-qr-sharing.py activate <home_id> <scene_id>', file=sys.stderr)
            return EXIT_SYNTAX_ERROR

        return client.activate(home_id, scene_id)

    if cmd == 'monitor':
        return client.monitor()

    if cmd == 'on':
        return client.activate_from_env('tuya_qr_sharing_scene_on')
    if cmd == 'off':
        return client.activate_from_env('tuya_qr_sharing_scene_off')
    return EXIT_OK

if __name__ == '__main__':
    sys.exit(main())

