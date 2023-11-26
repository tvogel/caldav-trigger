#!/usr/bin/env python3
# coding: utf-8

import logging
import json
import operator
import os
import dotenv
import sys
from typing import Any
from pathlib import Path
import requests
import pyqrcode
from tuya_sharing import LoginControl, Manager, SharingTokenListener, logger

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
    def __init__(self, dotenv_file) -> None:
        super().__init__()
        self.dotenv_file = dotenv_file

    def update_token(self, new_token_info: [str, Any]):
        LOGGER.debug("update token info : %s", new_token_info)
        global token_info
        token_info = new_token_info
        dotenv.set_key(self.dotenv_file, 'tuya_qr_sharing_token_info', json.dumps(token_info))

def main() -> int:

    logger.setLevel(LOGGER.getEffectiveLevel())

    dotenv_file = dotenv.find_dotenv()

    if not dotenv_file:
        source_path = Path(__file__).resolve()
        dotenv_file = os.path.join(os.getcwd(), '.env')

    dotenv.load_dotenv(dotenv_file)

    try:
        cmd = sys.argv[1]
    except IndexError:
        cmd = ''

    cmds = [ 'login', 'logout', 'homes', 'scenes', 'on', 'off' ]
    if not cmd in cmds:
        print('Syntax: tuya-qr-sharing.py (%s)' % '|'.join(cmds), file=sys.stderr)
        return EXIT_SYNTAX_ERROR;

    session = requests.session()

    user_code = os.environ.get('tuya_qr_sharing_user_code')
    username = os.environ.get('tuya_qr_sharing_username')
    terminal_id = os.environ.get('tuya_qr_sharing_terminal_id')
    endpoint = os.environ.get('tuya_qr_sharing_endpoint')

    global token_info
    try:
        token_info = json.loads(os.environ.get('tuya_qr_sharing_token_info'))
    except TypeError:
        token_info = None

    if cmd == 'logout':
        dotenv.unset_key(dotenv_file, 'tuya_qr_sharing_token_info')
        dotenv.unset_key(dotenv_file, 'tuya_qr_sharing_username')
        dotenv.unset_key(dotenv_file, 'tuya_qr_sharing_terminal_id')
        dotenv.unset_key(dotenv_file, 'tuya_qr_sharing_endpoint')
        return EXIT_OK

    if cmd == 'login':
        if token_info:
            print('You are already logged in.')
            return EXIT_OK

        if not user_code:
            user_code = input('SmartLife user-code from Settings/Account: ')
            dotenv.set_key(dotenv_file, 'tuya_qr_sharing_user_code', user_code)

        login_control = LoginControl()

        response = login_control.qr_code(CONF_CLIENT_ID, CONF_SCHEMA, user_code)

        if not response.get("success", False):
            print('Could not login: %i %s' % (response.get('code'), response.get('msg')), file = sys.stderr)
            return EXIT_AUTHENTICATION_FAILED

        qr_code = response["result"]["qrcode"]

        while True:
            print ('Please scan this in Smart-Life and authorize access:')
            print (pyqrcode.create(APP_QR_CODE_HEADER + qr_code, mode = 'binary').terminal())
            input ('Then, hit ENTER to continue.')

            ret, info = login_control.login_result(qr_code, CONF_CLIENT_ID, user_code)
            if not ret:
                print('Not authorized (yet): %i %s' % (info.get('code'), info.get('msg')), file = sys.stderr)
                print('Try again')
                continue

            token_info = {
                "t": info.get("t"),
                "uid": info.get("uid"),
                "expire_time": info.get("expire_time"),
                "access_token": info.get("access_token"),
                "refresh_token": info.get("refresh_token"),
            }

            username = info.get('username')
            terminal_id = info.get('terminal_id')
            endpoint = info.get('endpoint')
            dotenv.set_key(dotenv_file, 'tuya_qr_sharing_username', username)
            dotenv.set_key(dotenv_file, 'tuya_qr_sharing_token_info', json.dumps(token_info))
            dotenv.set_key(dotenv_file, 'tuya_qr_sharing_terminal_id', terminal_id)
            dotenv.set_key(dotenv_file, 'tuya_qr_sharing_endpoint', endpoint)
            break

        print('You are logged in.')
        return EXIT_OK

    if not token_info:
        print('Please log in first!', file = sys.stderr);
        return EXIT_AUTHENTICATION_FAILED

    token_listener = TokenListener(dotenv_file)
    tuya_sharing_manager = Manager(
        CONF_CLIENT_ID,
        user_code,
        terminal_id,
        endpoint,
        token_info,
        token_listener
    )

    try:
        tuya_sharing_manager.update_device_cache()
    except Exception as e:
        print('Cannot access Smartlife (%s)' % (e.args), file=sys.stderr)
        return EXIT_AUTHENTICATION_FAILED

    tuya_sharing_manager.user_homes.sort(key = operator.attrgetter('name'))

    if cmd == 'homes':
        print('Homes:')
        for home in tuya_sharing_manager.user_homes:
            print('%10s: %s' % (home.id, home.name))
        return EXIT_OK

    home_id = os.environ.get('tuya_qr_sharing_home')

    if cmd == 'scenes':
        for home in tuya_sharing_manager.user_homes:
            print('Scenes in home %s (%s):' % (home.name, home.id));
            for scene in sorted(tuya_sharing_manager.scene_repository.query_scenes([home.id]),
                   key = operator.attrgetter('name')):
                print('    %s: %s' % (scene.scene_id, scene.name));

        return EXIT_OK

    if not home_id:
        print('Set tuya_qr_sharing_home in .env first, in order to trigger scenes!', file=sys.stderr)
        return EXIT_HOME_MISSING

    if cmd == 'on':
        scene_id = os.environ.get('tuya_qr_sharing_scene_on')
        if not scene_id:
            print('Set tuya_qr_sharing_scene_on in .env first!', file=sys.stderr)
            return EXIT_SCENE_MISSING
    elif cmd == 'off':
        scene_id = os.environ.get('tuya_qr_sharing_scene_off')
        if not scene_id:
            print('Set tuya_qr_sharing_scene_off in .env first!', file=sys.stderr)
            return EXIT_SCENE_MISSING
    try:
        response = tuya_sharing_manager.scene_repository.trigger_scene(home_id, scene_id)
    except Exception as e:
        print('Error triggering scene (%s)' % (e.args), file=sys.stderr)
        return EXIT_TRIGGER_SCENE_FAILED

    if not response:
        print('Triggering scene reported failure', file=sys.stderr)
        return EXIT_TRIGGER_SCENE_FAILED
    print('tuya_sharing trigger succeeded.')
    return EXIT_OK

if __name__ == '__main__':
    sys.exit(main())

