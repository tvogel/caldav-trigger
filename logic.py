import vobject
import datetime
import time
import textwrap
import caldav

class HeatNeededIndicator:
    preheat_minutes = 0
    cooloff_minutes = 0
    no_heat_tag = None

    def __init__(self, preheat_minutes: int, cooloff_minutes: int, no_heat_tag: str):
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

    def is_needed(self, calendar: caldav.Calendar, now: datetime.datetime) -> bool:
        cooloff_timestamp = now + datetime.timedelta(minutes=self.cooloff_minutes,microseconds=1)
        preheat_timestamp = now + datetime.timedelta(minutes=self.preheat_minutes,microseconds=1)

        begin_search_window = now
        end_search_window = preheat_timestamp

        if self.cooloff_minutes < self.preheat_minutes:
            # can use shortcut to only search from cooloff_timestamp
            begin_search_window = cooloff_timestamp
            cooloff_timestamp = None

        for event in calendar.date_search(start=begin_search_window, end=end_search_window):
            vobj = event.vobject_instance
            try:
                if self.no_heat_tag is not None and vobj.vevent.description.value.find(self.no_heat_tag) >= 0:
                    if self.wrapper is not None:
                        try:
                            summary = vobj.vevent.summary.value
                        except:
                            summary = '<missing summary>'
                        try:
                            description = vobj.vevent.description.value
                        except:
                            description = '<missing description>'

                        print(self.wrapper.fill("Found event %s with %s in description:\n%s" %
                            (summary, self.no_heat_tag, description)))
                    continue
            except:
                # no description in event: fine!
                pass
            if cooloff_timestamp is not None and vobj.vevent.dtend.value <= cooloff_timestamp:
                # cooloff already has begun:
                continue

            if self.wrapper is not None:
                print(self.wrapper.fill("Found event that needs heating: %s" % vobj.vevent.summary.value))
            return True

        return False

