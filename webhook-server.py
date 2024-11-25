#!/usr/bin/env python3
# coding: utf-8

from functools import cache
import json
import logging
import os
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException
import uvicorn
import dotenv
import importlib
tuya_qr_sharing = importlib.import_module("tuya-qr-sharing")

app = FastAPI()
logger = logging.getLogger('uvicorn.error')

dotenv_file = dotenv.find_dotenv(usecwd=True) or dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

@cache
def get_config():
  logger.info(f"Configuration read from {dotenv_file}")
  scenes = dict(json.loads(os.getenv("webhook_server_scenes")))
  scene_info = "Scenes:\n"
  need_save = False
  skip = []
  for name, definition in scenes.items():
    scene_info += f"  {name}\n"
    if not 'home_id' in definition:
      scene_info += "    Missing home_id - ignoring\n"
      skip.append(name)
      continue
    if not 'scene_id' in definition:
      scene_info += "    Missing scene_id - ignoring\n"
      skip.append(name)
      continue
    if not 'key' in definition:
      scene_info += "    Setting key\n"
      definition['key'] = os.urandom(32).hex()
      need_save = True
  logger.info(scene_info)
  if need_save:
    dotenv.set_key(dotenv_file, "webhook_server_scenes", json.dumps(scenes, indent=2))
    logger.info("Configuration saved.")
  return { k: v for k, v in scenes.items() if k not in skip }

@cache
def get_client():
  client = tuya_qr_sharing.TuyaQrSharing(dotenv_file)
  if (result := client.connect()) != tuya_qr_sharing.EXIT_OK:
    raise HTTPException(status_code=500, detail="Failed to connect to Tuya")
  return client

ConfigDep = Annotated[dict, Depends(get_config)]
ClientDep = Annotated[tuya_qr_sharing.TuyaQrSharing, Depends(get_client)]

@app.get("/activate/{scene_id}")
async def activate(scene_id: str, key: str, config: ConfigDep, client: ClientDep):
  if scene_id not in config:
    raise HTTPException(status_code=404, detail="Scene not found")

  scene = config[scene_id]

  if key != scene['key']:
    raise HTTPException(status_code=401, detail="Invalid key")

  if (result := client.activate(scene['home_id'], scene['scene_id'])) != tuya_qr_sharing.EXIT_OK:
    raise HTTPException(status_code=500, detail=f"Failed to activate scene {scene_id} ({result})")

  return {"message": f"Scene {scene_id} activated successfully"}

if __name__ == "__main__":
  bind_host = os.getenv("webhook_server_host", "::")
  bind_port = int(os.getenv("webhook_server_port", "8000"))
  uvicorn.run(app, host=bind_host, port=bind_port, log_level="info")
