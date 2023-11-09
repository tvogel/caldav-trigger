#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import textwrap

import dotenv
import requests

EXIT_OK                = 0
EXIT_WEBREQUEST_FAILED = 1
EXIT_SYNTAX_ERROR      = 2

def float_or_none(value):
    return None if value is None else float(value)

def main() -> int:
    dotenv.load_dotenv()

    webhooks_url = os.getenv('webhooks_url')
    webhooks_key = os.getenv('webhooks_key')
    webhooks_heat_on_action = os.getenv('webhooks_heat_on_action')
    webhooks_heat_off_action = os.getenv('webhooks_heat_off_action')
    webhooks_timeout = float_or_none(os.getenv('webhooks_timeout'))

    try:
        need_heating = sys.argv[1]
    except IndexError:
        need_heating = ''

    if not need_heating in ['on','off']:
        print('Syntax: webhooks.py (on|off)', file=sys.stderr)
        return EXIT_SYNTAX_ERROR;

    need_heating = need_heating == 'on';

    wrapper = textwrap.TextWrapper(initial_indent=' ' * 0, width=80, subsequent_indent=' ' * 4)

    if webhooks_url:
        webhooks_action_url = str.format(
            webhooks_url
            , key=webhooks_key
            , action=webhooks_heat_on_action if need_heating else webhooks_heat_off_action)
        request = requests.get(webhooks_action_url, timeout=webhooks_timeout)
        print(wrapper.fill("Webhook request result: %i" % request.status_code))
        return EXIT_OK if request.status_code == 200 else EXIT_WEBREQUEST_FAILED

    return EXIT_OK

if __name__ == '__main__':
    sys.exit(main())
