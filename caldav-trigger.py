#!/usr/bin/env python3
# coding: utf-8

import caldav
import vobject
import datetime
import time
import requests
import textwrap
import dotenv
import sys
import os
# from IPython.lib.pretty import pretty

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

# main()

if cooloff_minutes >= preheat_minutes:
    print("Currently not supported: cooloff_minutes(%i) >= preheat_minutes(%i)" % (cooloff_minutes, preheat_minutes), file=sys.stderr)
    exit(1)

wrapper = textwrap.TextWrapper(initial_indent=' ' * 4, width=80, subsequent_indent=' ' * 8)

now = datetime.datetime.now().astimezone()
print("Checking at %s" % now)
begin_search_window = now + datetime.timedelta(minutes=cooloff_minutes)
end_search_window = now + datetime.timedelta(minutes=preheat_minutes)

any_needs_heating = False
with caldav.DAVClient(url=caldav_url, username=caldav_user, password=caldav_password) as client:
    principal = client.principal()
    calendar = principal.calendar(cal_id=calendar_id)
    for event in calendar.date_search(start=begin_search_window, end=end_search_window, verify_expand=True):
        vobj = event.vobject_instance
        # vobj.prettyPrint()
        no_heat = False
        try:
            # print("Description: ", vobj.vevent.description.value)
            if vobj.vevent.description.value.find(no_heat_tag) >= 0:
                print(wrapper.fill("Found event %s with %s in description:\n%s" %
                    (vobj.vevent.summary.value, no_heat_tag, vobj.vevent.description.value)))
                continue
        except:
            # no description in event: fine!
            pass
        print(wrapper.fill("Found event that needs heating: %s" % vobj.vevent.summary.value))
        any_needs_heating = True
        break

print(wrapper.fill("Heating needed" if any_needs_heating else "No heating needed"))
webhooks_action_url = webhooks_url % (webhooks_heat_on_action if any_needs_heating else webhooks_heat_off_action, webhooks_key)
request = requests.get(webhooks_action_url)
print(wrapper.fill("Webhook request result: %i" % request.status_code))

