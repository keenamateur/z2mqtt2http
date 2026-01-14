import json
import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_TOPIC, HTTP_DATA_PORT, HTTP_DEVICE_PORT, logger
from client_manager import client_manager
from http_client import http_client
from message_router import route_message

class MQTTHandler:
    def __init__(self):
        self.client = mqtt.Client()
        if MQTT_USERNAME and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT csatlakozva.")
            client.subscribe([(f"{MQTT_TOPIC}/#", 0), ("client/con_ip", 0)])
        else: logger.error(f"MQTT failure: {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try: payload_str = msg.payload.decode('utf-8')
        except: return

        if topic == "client/con_ip":
            client_manager.update_from_mqtt(payload_str)
            return

        try:
            payload = json.loads(payload_str) if payload_str else {}
            data, is_list = route_message(topic, payload)
            if data:
                if is_list: http_client.send_z2mqtt_data(data, HTTP_DATA_PORT)
                else: http_client.send_device_data(data, HTTP_DEVICE_PORT)
        except Exception as e: logger.error(f"Handler error: {e}")

    def start(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_forever()
