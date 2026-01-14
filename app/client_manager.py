import json
import os
import re
from config import CLIENTS_DATA_FILE, logger

class ClientManager:
    def __init__(self):
        self.data_file = CLIENTS_DATA_FILE
        self.clients = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading clients.json: {e}")
        return {}

    def _save(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.clients, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving clients.json: {e}")

    def update_from_mqtt(self, payload_str: str):
        try:
            if '/' not in payload_str: return
            name, ip = payload_str.split('/', 1)
            name, ip = name.strip(), ip.strip()
            
            if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip): return

            if self.clients.get(name) != ip:
                self.clients[name] = ip
                logger.info(f"Client data : {name} -> {ip}")
                self._save()
        except Exception as e:
            logger.error(f"Client update error: {e}")

    def get_all_ips(self) -> list:
        return list(self.clients.values())

client_manager = ClientManager()
