# Controlling smart heating valves from a CalDAV resource

This Python script can be used to check a CalDAV resource for occupation of a
room and control heating using generic web requests accordingly. This script
does the check just once for the current instance of time and invokes
correspondingly one of two web requests. In order to run this script regularly,
use `cron` or a similar service. I highly recommend using
[cronic](https://habilis.net/cronic/) for wrapping the call to this script in
cron. Also, logging can be achieved using `tee -a` to a file of your choice
(see [`caldav-trigger.sh`](caldav-trigger.sh)).

Even though this script was written for smart heating valves, it can of course
be used for anything that you can control in an on/off fashion using web
requests.

Parameters and credentials for accessing the CalDAV resource and invoking the
web request are configured using the system environment or a `.env` file. See
[`example.env`](example.env).

Furthermore, there are three parameters controlling the behavior:
* `preheat_minutes`: This time ahead of an occupation, the `heat_on` action is
  invoked.
* `cooloff_minutes`: This time ahead of the end of an occupation, the `heat_off`
  action is invoked.
* `no_heat_tag`: The command word is looked for in the descrption of an
  occupation. If found, the respective occuption is ignored and heating is not
  turned on.

  ⚠️ The command has to appear in the *description* of the occupation, not the
  *title*; there, it isn't taken into account - and it wouldn't look nice.
  It does not matter at which point in the description.

Because the room occupation calendar together with this script directly
determines heat costs 💸, users are advised to keep the calendar current such
that occupations needing heating are clearly recognizable:

* Tentative occupations such as reservations in advance should be marked using
  the `no_heat_tag` command.
* Multi-day occupation have to be entered as recurring events with the actually
  occupied times, i.e. use five events *Mo-Fr, 10-16h each* instead of a single
  continuous event *Mo 10h - Fr 16h*. In the latter case, the script would
  turn on heating also during the evenings and nights!

✅ If you run this script frequently using `cron`, e.g. every five minutes, also
short-term changes of the occupation are taken into account. Occupations can
be shortened, prolonged, deleted or created and the `no_heat_tag` can be added
or removed with short notice and the next run of the script will make the
changes effective.

## Code

The CalDAV and web request access is coded in the main script
[`caldav-trigger.py`](caldav-trigger.py), the evaluation logic is in
[`logic.py`](logic.py) with `pytest-mock` unit-tests in
[`logic_test.py`](logic_test.py).


