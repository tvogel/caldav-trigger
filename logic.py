import vobject
import datetime
import time
import textwrap
import caldav
from dataclasses import dataclass

@dataclass
class Event:
    summary: str
    description: str
    dtstart: datetime.datetime
    dtend: datetime.datetime

    def __repr__(self) -> str:
        return 'Event(%s, %s, %s, %s)' % (self.summary, self.description, self.dtstart, self.dtend)

    def dtstart_unix(self) -> int:
        return int(time.mktime(self.dtstart.timetuple()))

    @staticmethod
    def from_vobject(vobj: vobject.base.Component) -> 'Event':
        try:
            description = vobj.vevent.description.value
        except:
            description = None
        return Event(vobj.vevent.summary.value, description, vobj.vevent.dtstart.value.astimezone(), vobj.vevent.dtend.value.astimezone())

class HeatNeededIndicator:
    preheat_minutes = 0
    cooloff_minutes = 0
    no_heat_tag = None

    def __init__(self, preheat_minutes: int, cooloff_minutes: int, no_heat_tag: str | None = None) -> None:
        self.wrapper = None
        self.preheat_minutes = preheat_minutes
        self.cooloff_minutes = cooloff_minutes
        self.no_heat_tag = no_heat_tag

    def __repr__(self) -> str:
        if self.no_heat_tag is None:
            return 'HeatNeededIndicator(%i, %i)' % (self.preheat_minutes, self.cooloff_minutes)
        return 'HeatNeededIndicator(%i, %i, "%s")' % (self.preheat_minutes, self.cooloff_minutes, self.no_heat_tag)

    def set_wrapper(self, wrapper: textwrap.TextWrapper) -> None:
        self.wrapper = wrapper

    def get_next_events(self, calendar: caldav.Calendar, now: datetime.datetime) -> list[Event]:
        events = []
        cooloff_timestamp = now + datetime.timedelta(minutes=self.cooloff_minutes,seconds=1)
        preheat_timestamp = now + datetime.timedelta(minutes=self.preheat_minutes,seconds=1)

        begin_search_window = now
        end_search_window = preheat_timestamp

        if self.cooloff_minutes < self.preheat_minutes:
            # can use shortcut to only search from cooloff_timestamp
            begin_search_window = cooloff_timestamp
            cooloff_timestamp = None

        for event in calendar.date_search(start=begin_search_window, end=end_search_window):
            vobj = event.vobject_instance
            try:
                summary = vobj.vevent.summary.value
            except: # Missing summary
                if self.wrapper is not None:
                    print(self.wrapper.fill("Skipping unnamed event!"))
                continue
            try:
                if self.no_heat_tag is not None and vobj.vevent.description.value.find(self.no_heat_tag) >= 0:
                    if self.wrapper is not None:
                        print(self.wrapper.fill("Found event %s with %s in description:\n%s" %
                            (summary, self.no_heat_tag, vobj.vevent.description.value)))
                    continue
            except:
                # no description in event: fine!
                pass
            if cooloff_timestamp is not None and vobj.vevent.dtend.value <= cooloff_timestamp:
                # cooloff already has begun:
                continue

            if self.wrapper is not None:
                print(self.wrapper.fill("Found event that needs heating: %s" % summary))

            events.append(Event.from_vobject(vobj))

        return events

    def is_needed(self, calendar: caldav.Calendar, now: datetime.datetime) -> bool:
        return len(self.get_next_events(calendar, now)) > 0

