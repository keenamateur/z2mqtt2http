import requests
from typing import Any
from client_manager import client_manager
from config import logger

class HTTPClient:
    def send_z2mqtt_data(self, data: Any, port: int):
        ips = client_manager.get_all_ips()
        for ip in ips:
            try:
                url = f"http://{ip}:{port}"
                headers = {'Content-Type': 'application/json; charset=utf-8'}
                #  GET method with JSON body
                requests.get(url, json=data, headers=headers, timeout=15)
                logger.debug(f"Device list elküldve -> {ip}")
            except Exception as e:
                logger.error(f"HTTP küldési hiba (lista) -> {ip}: {e}")

    def send_device_data(self, data: Any, port: int):
        ips = client_manager.get_all_ips()
        for ip in ips:
            try:
                url = f"http://{ip}:{port}"
                # GET with query parameter
                requests.get(url, params=data, timeout=10)
                logger.debug(f"Eszköz adat elküldve -> {ip}")
            except Exception as e:
                logger.error(f"HTTP küldési hiba (státusz) -> {ip}: {e}")

http_client = HTTPClient()