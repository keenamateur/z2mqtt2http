import os
import logging
import sys

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()
logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("z2mqtt2http")

MQTT_BROKER = os.getenv('MQTT_BROKER', '172.30.10.222')
MQTT_PORT = int(os.getenv('MQTT_PORT', 52888))
MQTT_USERNAME = os.getenv('MQTT_USER', None)
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'gtl')

HTTP_DEVICE_PORT = int(os.getenv('HTTP_DEVICE_PORT', 1905))
HTTP_DATA_PORT = int(os.getenv('HTTP_DATA_PORT', 1904))

TIMEOUT_PENDING_MAINCACHE = int(os.getenv('TIMEOUT_PENDING_MAINCACHE', 604800))
TIMEOUT_PENDING_GETREQUEST = int(os.getenv('TIMEOUT_PENDING_GETREQUEST', 5))
CLIENTS_DATA_FILE = os.getenv('CLIENTS_DATA_FILE', 'clients.json')

ALLOWED_ROOMS = []

def update_allowed_rooms(rooms: list):
    global ALLOWED_ROOMS
    if not rooms: return
    new_rooms = list(set(ALLOWED_ROOMS + rooms))
    if len(new_rooms) > len(ALLOWED_ROOMS):
        ALLOWED_ROOMS[:] = new_rooms
        logger.info(f"Updated ALLOWED_ROOMS: {ALLOWED_ROOMS}")