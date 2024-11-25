# Controlling smart heating valves from a CalDAV calendar resource

This Python script can be used to check a CalDAV resource for occupation of a
room and control heating using web requests or Tuya scenes accordingly. This
script does the check just once for the current instance of time and
consequently invokes one of two configured actions. In order to run this script
regularly, use `cron` or a similar service. I highly recommend using
[cronic](https://habilis.net/cronic/) for wrapping the call to this script in
cron. Also, logging can be achieved using `tee -a` to a file of your choice
(see [`caldav-trigger.sh`](caldav-trigger.sh)).

Even though this script was written for smart heating valves, it can of course
be used for anything that you can control in an *on*/*off* fashion using web
requests.

Parameters and credentials for accessing the CalDAV resource and invoking the
intended actions are configured using the system environment or a `.env` file.
See [`example.env`](example.env).

There are three parameters controlling the behavior:
* `preheat_minutes`: This time ahead of an occupation, the `heat_on` action is
  invoked.
* `cooloff_minutes`: This time ahead of the end of an occupation, the `heat_off`
  action is invoked.
* `no_heat_tag`: This command word is looked for in the descrption of an
  occupation. If found, the respective entry is ignored and heating is not
  turned on.

  ⚠️ The command has to appear in the *description* of the occupation, not the
  *title*; there, it isn't taken into account - and it wouldn't look nice.
  It does not matter at which point in the description.

Because the room occupation calendar together with this script directly
determines heat costs 💸, users are advised to keep the calendar current such
that occupations needing heating are clearly recognizable:

* Tentative occupations such as reservations in advance should be marked using
  the `no_heat_tag` command.
* Multi-day occupation has to be entered as recurring events with the actually
  occupied times, i.e. use five events *Mo-Fr, 10-16h each* instead of a single
  continuous event *Mo 10h - Fr 16h*. In the latter case, the script would
  turn on heating also during the evenings and nights!

✅ If you run this script frequently using `cron`, e.g. every five minutes, also
short-term changes of the occupation are taken into account. Occupations can
be shortened, prolonged, deleted or created and the `no_heat_tag` can be added
or removed with short notice and the next run of the script will make the
changes effective.

## Actions

In order to turn the heating *on* or *off*, an action script configured in
`.env` is invoked with `on` or `off` as parameter. Currently, these are the
options:

- [webhooks.py](webhooks.py): This script allows to call generic web-hooks, e.g.
  on [IFTTT](https://ifttt.com)
- [iot-tuya.py](iot-tuya.py): This script allows to invoke Tuya scenes via the
  Tuya Open API. You'll need to register at https://iot.tuya.com/, create a
  cloud project and link your Tuya/SmartLife account there.
- [tuya-qr-sharing.py](tuya-qr-sharing.py): This script will invoke Tuya scenes
  via the
  [Tuya Device Sharing SDK](https://github.com/tuya/tuya-device-sharing-sdk).
  This is easier because you can authorize the script via scanning a QR code in
  your Tuya or SmartLife app without registering a project on
  https://iot.tuya.com/. This script can also trigger arbitrary scenes using the
  `activate <home_id> <scene_id>` command which is used by the webhook server.

You can easily adapt this logic to your own action scripts by implementing new
action scripts. Pull-requests are welcome!

The [iot-tuya.py](iot-tuya.py) and [tuya-qr-sharing.py](tuya-qr-sharing.py)
scripts have additional commands that help in configuring the desired Tuya
scenes and performing the QR authorization step. Please run them without
command line parameters to see the options.

## Webhook server
As IFTTT has decided to make web-hook triggers pay-only and my use of it does
not justify the expense, I have implemented a basic web-hook server. It
currently only speaks unencrypted HTTP and therefore is intended to be run
behind a reverse-proxy such as `nginx` to provide the SSL encryption layer.
See [`example.env`](example.env) for the host/port and end-point configuration.


## Code

The CalDAV and action invocation is coded in the main script
[`caldav-trigger.py`](caldav-trigger.py), the evaluation logic is in
[`logic.py`](logic.py) with `pytest-mock` unit-tests in
[`logic_test.py`](logic_test.py).

The actions are implemented in the respective scripts, linked above.

All dependencies are given in [requirements.txt](requirements.txt).

