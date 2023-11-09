#!/usr/bin/env python3
# coding: utf-8

import logging
from tuya_iot import TuyaOpenAPI, TUYA_LOGGER
import json
import os
import dotenv
import sys

EXIT_OK = 0
EXIT_AUTHENTICATION_FAILED = 1
EXIT_SYNTAX_ERROR = 2
EXIT_LIST_HOMES_FAILED = 3
EXIT_TUYA_HOME_MISSING = 4
EXIT_LIST_SCENES_FAILED = 5
EXIT_TUYA_SCENE_MISSING = 6
EXIT_TRIGGER_SCENE_FAILED = 7

def main() -> int:
    dotenv.load_dotenv()

    # Init
    # TUYA_LOGGER.setLevel(logging.DEBUG)
    openapi = TuyaOpenAPI(
        os.environ.get('tuya_endpoint_url'),
        os.environ.get('tuya_access_id'),
        os.environ.get('tuya_access_secret'))
    response = openapi.connect(
        os.environ.get('tuya_username'),
        os.environ.get('tuya_password'),
        os.environ.get('tuya_country_code'),
        os.environ.get('tuya_schema'))

    if not response['success']:
        print('Authentication failed: %s' % response['msg'], file=sys.stderr)
        return EXIT_AUTHENTICATION_FAILED

    uid = response['result']['uid']

    try:
        cmd = sys.argv[1]
    except IndexError:
        cmd = ''

    if not cmd in [ 'homes', 'scenes', 'on', 'off' ]:
        print('Syntax: tuya.py (on|off|homes|scenes)', file=sys.stderr)
        return EXIT_SYNTAX_ERROR;

    if cmd == 'homes':
        response = openapi.get('/v1.0/users/{uid}/homes'.format(uid = uid))
        if not response['success']:
            print('Error listing homes: %s' % response['msg'], file=sys.stderr)
            return EXIT_LIST_HOMES_FAILED

        print('Homes:')
        for home in response['result']:
            print('%s: %s' % (home['name'], home['home_id']))
        return EXIT_OK

    home_id = os.environ.get('tuya_home')

    if cmd == 'scenes':
        if not home_id:
            print('Set tuya_home in .env first, in order to list scenes!', file=sys.stderr)
            return EXIT_TUYA_HOME_MISSING
        response = openapi.get('/v1.1/homes/{home_id}/scenes'.format(home_id = home_id))
        if not response['success']:
            print('Error listing scenes: %s' % response['msg'], file=sys.stderr)
            return EXIT_LIST_SCENES_FAILED

        for scene in response['result']:
            print('%s: %s' % (scene['name'], scene['scene_id']))
        return EXIT_OK

    if not home_id:
        print('Set tuya_home in .env first, in order to trigger scenes!', file=sys.stderr)
        return EXIT_TUYA_HOME_MISSING

    if cmd == 'on':
        scene_id = os.environ.get('tuya_scene_on')
        if not scene_id:
            print('Set tuya_scene_on in .env first!', file=sys.stderr)
            return EXIT_TUYA_SCENE_MISSING
    elif cmd == 'off':
        scene_id = os.environ.get('tuya_scene_off')
        if not scene_id:
            print('Set tuya_scene_off in .env first!', file=sys.stderr)
            return EXIT_TUYA_SCENE_MISSING

    response = openapi.post('/v1.0/homes/{home_id}/scenes/{scene_id}/trigger'.format(home_id = home_id, scene_id = scene_id))
    if not response['success']:
        print('Error triggering scene: %s' % response['msg'], file=sys.stderr)
        return EXIT_TRIGGER_SCENE_FAILED
    print('Tuya trigger succeeded.')
    return EXIT_OK

if __name__ == '__main__':
    sys.exit(main())
