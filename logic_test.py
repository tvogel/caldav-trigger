from array import array
import datetime
import string
import textwrap
from typing import Callable

import caldav
import vobject

from logic import *

EventData = tuple[datetime.datetime, datetime.datetime, str, str]
Events = list[EventData]
DataRow = tuple[datetime.datetime, bool]
Data = list[DataRow]

def make_event(start: datetime.datetime, end: datetime.datetime, summary: str, description: str = None) -> caldav.Event:
    vobj = vobject.iCalendar()
    vobj.add('vevent')
    vobj.vevent.add('dtstart').value = start
    vobj.vevent.add('dtend').value = end
    vobj.vevent.add('summary').value = summary
    if description is not None:
        vobj.vevent.add('description').value = description
    event = caldav.Event()
    event.vobject_instance = vobj
    return event

def make_datetime(hour: int, minute: int, second: int = 0, microsecond: int = 0) -> datetime.datetime:
    return datetime.datetime(1980,1,1,hour,minute,second,microsecond,tzinfo=datetime.timezone.utc)

def make_date_search(testEvents: Events) -> Callable:
    def date_search(start, end=None, compfilter="VEVENT", expand="maybe", verify_expand=False):
        result = []
        for (event_start, event_end, summary, description) in testEvents:
            if event_start < end and event_end >= start:
                result.append(make_event(event_start, event_end, summary, description))
        return result
    return date_search

def data_drive_test_is_needed(mocker, indicator: HeatNeededIndicator, test_events: Events, test_data: Data) -> None:
    wrapper = textwrap.TextWrapper(width=80, initial_indent='', subsequent_indent=' ' * 4)
    indicator.set_wrapper(wrapper)

    mock_calendar = mocker.create_autospec(caldav.Calendar, instance = True)
    mock_calendar.date_search.side_effect = make_date_search(test_events)

    for (now, expected_result) in test_data:
        print('now:', now, 'expectedResult:', expected_result)
        actual_result = indicator.is_needed(mock_calendar, now)
        assert actual_result == expected_result, str((test_events, now, expected_result))

def test_is_needed_no_preheat_or_cooldown(mocker):
    indicator = HeatNeededIndicator(preheat_minutes=0, cooloff_minutes=0, no_heat_tag='!cold!')

    test_events = [
        # ( start,                   end,                     summary,                description or None)
          ( make_datetime(12, 0, 0), make_datetime(14, 0, 0), 'Test event noon',      None )
        , ( make_datetime(14, 0, 0), make_datetime(14,30, 0), 'Test cold event',      'This event is !cold!. Yay.' )
        , ( make_datetime(16,15, 0), make_datetime(18, 0, 0), 'Test event afternoon', None )
        , ( make_datetime(20, 0, 0), make_datetime(20, 0, 0), 'Borderline event',     None )
        ]

    test_data = [
        # (now,                          expected_result)
          ( make_datetime(11,59,59,999), False )
        , ( make_datetime(12, 0, 0,  0), True )
        , ( make_datetime(13,59,59,999), True )
        , ( make_datetime(14, 0, 0,  0), False )
        , ( make_datetime(14,15, 0,  0), False )
        , ( make_datetime(16,14,59,999), False )
        , ( make_datetime(16,15, 0,  0), True )
        , ( make_datetime(17,59,59,999), True )
        , ( make_datetime(18, 0, 0,  0), False )
        , ( make_datetime(20, 0, 0,  0), False ) # Events shorter or equal length to (cooloff_minutes - preheat_minutes) are effectively ignored
    ]

    data_drive_test_is_needed(mocker, indicator, test_events, test_data)

def test_is_needed_equal_preheat_and_cooldown(mocker):
    indicator = HeatNeededIndicator(preheat_minutes=30, cooloff_minutes=30, no_heat_tag='!cold!')

    test_events = [
        # ( start,                   end,                     summary,                description or None)
          ( make_datetime(12, 0, 0), make_datetime(14, 0, 0), 'Test event noon',      None )
        , ( make_datetime(14, 0, 0), make_datetime(14,30, 0), 'Test cold event',      'This event is !cold!. Yay.' )
        , ( make_datetime(16,15, 0), make_datetime(18, 0, 0), 'Test event afternoon', None )
        , ( make_datetime(20, 0, 0), make_datetime(20, 0, 0), 'Borderline event',     None )
        ]

    test_data = [
        # (now,                          expected_result)
          ( make_datetime(11,29,59,999), False )
        , ( make_datetime(11,30, 0,  0), True )
        , ( make_datetime(13,29,59,999), True )
        , ( make_datetime(13,30, 0,  0), False )
        , ( make_datetime(13,45, 0,  0), False )
        , ( make_datetime(15,44,59,999), False )
        , ( make_datetime(15,45, 0,  0), True )
        , ( make_datetime(17,29,59,999), True )
        , ( make_datetime(17,30, 0,  0), False )
        , ( make_datetime(19,30, 0,  0), False ) # Events shorter or equal length to (cooloff_minutes - preheat_minutes) are effectively ignored
    ]

    data_drive_test_is_needed(mocker, indicator, test_events, test_data)

def test_is_needed_longer_preheat_than_cooldown(mocker):
    indicator = HeatNeededIndicator(preheat_minutes=60, cooloff_minutes=30, no_heat_tag='!cold!')

    test_events = [
        # ( start,                   end,                     summary,                description or None )
          ( make_datetime(12, 0, 0), make_datetime(14, 0, 0), 'Test event noon',      None )
        , ( make_datetime(14, 0, 0), make_datetime(14,30, 0), 'Test cold event',      'This event is !cold!. Yay.' )
        , ( make_datetime(16,15, 0), make_datetime(18, 0, 0), 'Test event afternoon', None )
        , ( make_datetime(20, 0, 0), make_datetime(20, 0, 0), 'Borderline event',     None )
        ]

    test_data = [
        # ( now,                         expected_result )
          ( make_datetime(10,59,59,999), False )
        , ( make_datetime(11, 0, 0,  0), True )
        , ( make_datetime(13,29,59,999), True )
        , ( make_datetime(13,30, 0,  0), False )
        , ( make_datetime(13,45, 0,  0), False )
        , ( make_datetime(15,14,59,999), False )
        , ( make_datetime(15,15, 0,  0), True )
        , ( make_datetime(17,29,59,999), True )
        , ( make_datetime(17,30, 0,  0), False )
        , ( make_datetime(19, 0, 0,  0), True ) # hm, is this a bug? Implement minimum length filter?
        , ( make_datetime(19,29,59,999), True ) # hm, is this a bug? Implement minimum length filter?
        , ( make_datetime(19,30, 0,  0), False )
    ]

    data_drive_test_is_needed(mocker, indicator, test_events, test_data)

def test_is_needed_shorter_preheat_than_cooldown(mocker):
    indicator = HeatNeededIndicator(preheat_minutes=30, cooloff_minutes=60, no_heat_tag='!cold!')

    test_events = [
        # ( start,                   end,                     summary,                description or None )
          ( make_datetime(12, 0, 0), make_datetime(14, 0, 0), 'Test event noon',      None )
        , ( make_datetime(14, 0, 0), make_datetime(14,30, 0), 'Test cold event',      'This event is !cold!. Yay.' )
        , ( make_datetime(16,15, 0), make_datetime(18, 0, 0), 'Test event afternoon', None )
        , ( make_datetime(20, 0, 0), make_datetime(20,30, 0), 'Borderline event',     None )
        ]

    test_data = [
        # (now,                          expected_result)
          ( make_datetime(11,29,59,999), False )
        , ( make_datetime(11,30, 0,  0), True )
        , ( make_datetime(12,59,59,999), True )
        , ( make_datetime(13, 0, 0,  0), False )
        , ( make_datetime(13,45, 0,  0), False )
        , ( make_datetime(15,44,59,999), False )
        , ( make_datetime(15,45, 0,  0), True )
        , ( make_datetime(16,59,59,999), True )
        , ( make_datetime(17, 0, 0,  0), False )
        , ( make_datetime(19,30, 0,  0), False ) # Events shorter or equal length to (cooloff_minutes - preheat_minutes) are effectively ignored
        ]

    data_drive_test_is_needed(mocker, indicator, test_events, test_data)

def test_is_needed_overlapping_events(mocker):
    indicator = HeatNeededIndicator(preheat_minutes=30, cooloff_minutes=60, no_heat_tag='!cold!')

    test_events = [
        # ( start,                   end,                     summary,                description or None )
          ( make_datetime(12, 0, 0), make_datetime(14, 0, 0), 'Test event noon',      None )
        , ( make_datetime(12,45, 0), make_datetime(14,30, 0), 'Test cold event',      'This event is !cold!. Yay.' )
        , ( make_datetime(14,15, 0), make_datetime(15, 0, 0), 'Test event afternoon', None )
        , ( make_datetime(14,45, 0), make_datetime(15,20, 0), 'Test event afternoon', None )
        ]

    test_data = [
        # (now,                          expected_result)
          ( make_datetime(11,29,59,999), False )
        , ( make_datetime(11,30, 0,  0), True )
        , ( make_datetime(12,59,59,999), True )
        , ( make_datetime(13, 0, 0,  0), False )
        , ( make_datetime(13,30, 0,  0), False )
        , ( make_datetime(13,44,59,999), False )
        , ( make_datetime(13,45, 0,  0), True )
        , ( make_datetime(13,59,59,999), True )
        , ( make_datetime(14, 0, 0,  0), False ) # bug?
                                                # Happens because each event has preheat / cooloff applied individually and then,
                                                # they donot in fact overlap. Could first join overlaps and then apply margins.
        , ( make_datetime(14,14,59,999), False )
        , ( make_datetime(14,15, 0,  0), True )
        , ( make_datetime(14,19,59,999), True )
        , ( make_datetime(14,20, 0,  0), False )
        ]

    data_drive_test_is_needed(mocker, indicator, test_events, test_data)
