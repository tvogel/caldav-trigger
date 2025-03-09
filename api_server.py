#!/usr/bin/env python3
# coding: utf-8

import textwrap
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR
from logic import HeatNeededIndicator, Event
import caldav
import datetime
import os
import json
import dotenv

dotenv.load_dotenv()

app = FastAPI()
security = HTTPBasic(realm=os.getenv("api_realm"))

users_db = json.loads(os.getenv("api_users"))

indicator = HeatNeededIndicator(
    preheat_minutes=0,  # Placeholder, will be set dynamically
    cooloff_minutes=0,  # Placeholder, will be set dynamically
    no_heat_tag=os.getenv("no_heat_tag")
)

wrapper = textwrap.TextWrapper(initial_indent=' ' * 4, width=80, subsequent_indent=' ' * 8)
indicator.set_wrapper(wrapper)

def create_caldav_client():
    return caldav.DAVClient(
        url=os.getenv("caldav_url"),
        username=os.getenv("caldav_user"),
        password=os.getenv("caldav_password"),
        timeout=float(os.getenv("caldav_timeout", 0)) or None
    )

client = create_caldav_client()
principal = client.principal()
calendar_id = os.getenv("calendar_id")
calendar = principal.calendar(cal_id=calendar_id)

def authenticate_user(username: str, password: str):
    if username in users_db and users_db[username] == password:
        return True
    return False

def get_calendar_events(now: datetime.datetime):
    global client, principal, calendar
    try:
        events = indicator.get_next_events(calendar, now.astimezone())
        return events
    except caldav.error.CaldavError:
        # Reset client on timeout or other CalDAV errors
        client = create_caldav_client()
        principal = client.principal()
        calendar = principal.calendar(cal_id=calendar_id)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve events from CalDAV server. Please try again later."
        )

@app.get("/next-events")
def read_next_events(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    preheat_minutes: Annotated[int, Query(..., ge=0, description="Preheat duration in minutes")],
    cooloff_minutes: Annotated[int, Query(..., ge=0, description="Cooloff duration in minutes")],
    now: datetime.datetime = Query(default_factory=datetime.datetime.now, description="Current date-time")
) -> list[Event]:
    username = credentials.username
    password = credentials.password
    if not authenticate_user(username, password):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": f'Basic realm="{security.realm}"'},
        )

    indicator.preheat_minutes = preheat_minutes
    indicator.cooloff_minutes = cooloff_minutes
    events = get_calendar_events(now)
    return events

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("api_server_host", "127.0.0.1"),
        port=int(os.getenv("api_server_port", 8000)),
        root_path=os.getenv("api_server_root_path", "/"),
        log_level="info"
    )
