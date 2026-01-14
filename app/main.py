import signal
import sys
import threading
import time
from config import logger
from mqtt_handler import MQTTHandler
from services import device_status_manager, get_response_cache

def cleanup_loop():
    while True:
        time.sleep(300)
        device_status_manager.cleanup()
        get_response_cache.cleanup()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))
    threading.Thread(target=cleanup_loop, daemon=True).start()
    logger.info("Z2MQTT2HTTP Starting...")
    MQTTHandler().start()