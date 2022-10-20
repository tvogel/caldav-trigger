#!/bin/bash
set -o errexit
caldav-trigger.py | tee -a ~/logs/caldav-trigger.log
