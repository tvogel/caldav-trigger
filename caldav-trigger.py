#!/usr/bin/env python3
# coding: utf-8

import datetime
import os
import sys
import textwrap

import caldav
import dotenv
import subprocess

from logic import HeatNeededIndicator

EXIT_OK                = 0
EXIT_ACTION_FAILED     = 1

def main() -> int:
    dotenv.load_dotenv()

    caldav_url = os.getenv('caldav_url')
    caldav_user = os.getenv('caldav_user')
    caldav_password = os.getenv('caldav_password')
    caldav_timeout = float_or_none(os.getenv('caldav_timeout'))

    calendar_id = os.getenv('calendar_id')
    no_heat_tag = os.getenv('no_heat_tag')
    action = os.getenv('action')

    preheat_minutes = int(os.getenv('preheat_minutes'))
    cooloff_minutes = int(os.getenv('cooloff_minutes'))

    now = datetime.datetime.now().astimezone()
    print("Checking at %s" % now)

    wrapper = textwrap.TextWrapper(initial_indent=' ' * 4, width=80, subsequent_indent=' ' * 8)

    heat_needed_indicator = HeatNeededIndicator(preheat_minutes, cooloff_minutes, no_heat_tag)
    heat_needed_indicator.set_wrapper(wrapper) # for diagnostic output

    with caldav.DAVClient(url=caldav_url, username=caldav_user, password=caldav_password, timeout=caldav_timeout) as client:
        principal = client.principal()
        calendar = principal.calendar(cal_id=calendar_id)
        need_heating = heat_needed_indicator.is_needed(calendar, now)

    print(wrapper.fill("Heating needed" if need_heating else "No heating needed"))

    action_result = subprocess.run([action, 'on' if need_heating else 'off' ], stdout=subprocess.PIPE)
    print(wrapper.fill(action_result.stdout.decode()))
    return EXIT_OK if action_result.returncode == 0 else EXIT_ACTION_FAILED

if __name__ == '__main__':
    sys.exit(main())
