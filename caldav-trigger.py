#!/usr/bin/env python3
# coding: utf-8

import datetime
import os
import sys
import textwrap

import caldav
import dotenv
import requests

from logic import HeatNeededIndicator

EXIT_OK                = 0
EXIT_WEBREQUEST_FAILED = 1

def main() -> int:
    dotenv.load_dotenv()

    caldav_url = os.getenv('caldav_url')
    caldav_user = os.getenv('caldav_user')
    caldav_password = os.getenv('caldav_password')
    calendar_id = os.getenv('calendar_id')
    no_heat_tag = os.getenv('no_heat_tag')

    preheat_minutes = int(os.getenv('preheat_minutes'))
    cooloff_minutes = int(os.getenv('cooloff_minutes'))

    webhooks_url = os.getenv('webhooks_url')
    webhooks_key = os.getenv('webhooks_key')
    webhooks_heat_on_action = os.getenv('webhooks_heat_on_action')
    webhooks_heat_off_action = os.getenv('webhooks_heat_off_action')

    now = datetime.datetime.now().astimezone()
    print("Checking at %s" % now)

    wrapper = textwrap.TextWrapper(initial_indent=' ' * 4, width=80, subsequent_indent=' ' * 8)

    heat_needed_indicator = HeatNeededIndicator(preheat_minutes, cooloff_minutes, no_heat_tag)
    heat_needed_indicator.set_wrapper(wrapper) # for diagnostic output

    with caldav.DAVClient(url=caldav_url, username=caldav_user, password=caldav_password) as client:
        principal = client.principal()
        calendar = principal.calendar(cal_id=calendar_id)
        need_heating = heat_needed_indicator.is_needed(calendar, now)

    print(wrapper.fill("Heating needed" if need_heating else "No heating needed"))

    if webhooks_url:
        webhooks_action_url = str.format(
            webhooks_url
            , key=webhooks_key
            , action=webhooks_heat_on_action if need_heating else webhooks_heat_off_action)
        request = requests.get(webhooks_action_url)
        print(wrapper.fill("Webhook request result: %i" % request.status_code))
        return EXIT_OK if request.status_code == 200 else EXIT_WEBREQUEST_FAILED

    return EXIT_OK

if __name__ == '__main__':
    sys.exit(main())
