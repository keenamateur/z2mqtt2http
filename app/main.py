import os
import json
import time
import logging
import re
import threading
import sys
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

import paho.mqtt.client as mqtt
import requests


# ==============================================================================
# FILE: ip_client.py
# ==============================================================================
logger = logging.getLogger(__name__)

class IPClient:
    def __init__(self):
        self.current_ip = os.getenv('HTTP_CLIENT_IP', '192.168.2.100')
        logger.info(f"IPClient initialized. Initial IP: {self.current_ip}")
    
    def update_ip_from_message(self, topic: str, payload: Any) -> bool:
        """Update IP address from MQTT message"""
        try:
            if topic != "client/con_ip":
                return False
            
            new_ip = None
            if isinstance(payload, dict) and 'ip' in payload:
                new_ip = payload['ip']
            elif isinstance(payload, str):
                try:
                    payload_dict = json.loads(payload)
                    if isinstance(payload_dict, dict) and 'ip' in payload_dict:
                        new_ip = payload_dict['ip']
                    else:
                        new_ip = payload.strip()
                except json.JSONDecodeError:
                    new_ip = payload.strip()
            
            if not new_ip:
                logger.warning("Empty IP address received")
                return False
            
            if not self._validate_ip(new_ip):
                logger.warning(f"Invalid IP address received: {new_ip}")
                return False
            
            if new_ip != self.current_ip:
                logger.info(f"IP address updated: {self.current_ip} -> {new_ip}")
                self.current_ip = new_ip
                self._update_config_file(new_ip)
                return True
            else:
                logger.debug("IP address has not changed")
                return False
                
        except Exception as e:
            logger.error(f"Error updating IP address: {e}")
            return False
    
    def _validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip):
            return False
        
        parts = ip.split('.')
        for part in parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                return False
        
        return True
    
    def _update_config_file(self, new_ip: str):
        """Update .env file with new IP address"""
        try:
            env_file = '.env'
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith('HTTP_CLIENT_IP='):
                        lines[i] = f'HTTP_CLIENT_IP={new_ip}\n'
                        updated = True
                        break
                
                if updated:
                    with open(env_file, 'w') as f:
                        f.writelines(lines)
                    logger.info(f".env file updated with new IP: {new_ip}")
                else:
                    with open(env_file, 'a') as f:
                        f.write(f'\nHTTP_CLIENT_IP={new_ip}\n')
                    logger.info(f"HTTP_CLIENT_IP added to .env file: {new_ip}")
            
            os.environ['HTTP_CLIENT_IP'] = new_ip
            logger.info(f"Environment variable updated: HTTP_CLIENT_IP={new_ip}")
            
        except Exception as e:
            logger.error(f"Error updating configuration file: {e}")
    
    def get_current_ip(self) -> str:
        """Get the current IP address"""
        return self.current_ip

# Global instance
ip_client = IPClient()


# ==============================================================================
# FILE: config.py
# ==============================================================================
# MQTT Configuration
MQTT_BROKER = os.getenv('MQTT_BROKER', '192.168.1.100')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_USERNAME = os.getenv('MQTT_USER', None)
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'topic')

# HTTP Configuration - DYNAMIC IP
HTTP_CLIENT_IP = os.getenv('HTTP_CLIENT_IP', ip_client.get_current_ip())
HTTP_DEVICE_PORT = int(os.getenv('HTTP_DEVICE_PORT', 1905)) # adjust
HTTP_DATA_PORT = int(os.getenv('HTTP_DATA_PORT', 1904)) # adjust

# Timeout Configurations
TIMEOUT_PENDING_MAINCACHE = int(os.getenv('TIMEOUT_PENDING_MAINCACHE', 43200))  # 12 hours
TIMEOUT_PENDING_GETREQUEST = int(os.getenv('TIMEOUT_PENDING_GETREQUEST', 5))    # 5 seconds 

ALLOWED_ROOMS = []

def update_allowed_rooms(rooms: list):
    """Dynamically update allowed rooms from device list"""
    global ALLOWED_ROOMS
    ALLOWED_ROOMS = list(set(ALLOWED_ROOMS + rooms))
    print(f"Updated ALLOWED_ROOMS: {ALLOWED_ROOMS}")

def save_z2mqtt_data(data: dict):
    """Save processed data to z2mqtt_data.json"""
    try:
        with open('z2mqtt_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Data saved to /app/z2mqtt_data.json")
    except Exception as e:
        print(f"Error saving data: {e}")


# ==============================================================================
# FILE: http_client.py
# ==============================================================================
class HTTPClient:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def send_z2mqtt_data(self, data, port):
        """Send device list data via HTTP GET with a JSON body."""
        try:
            current_ip = ip_client.get_current_ip()
            url = f"http://{current_ip}:{port}"
            
            self.logger.info(f"Sending device list GET request to: {url}")
            self.logger.debug(f"Data to send: {json.dumps(data, ensure_ascii=False)[:500]}...")
            
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                self.logger.info(f"Data sent successfully to {url}")
                self.logger.debug(f"Response: {response.text}")
                return True
            else:
                self.logger.error(f"Send error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"HTTP send error: {e}")
            return False
    
    def send_device_data(self, data, port):
        """Send device status data via HTTP GET request with URL parameters."""
        try:
            current_ip = ip_client.get_current_ip()
            url = f"http://{current_ip}:{port}"
            
            self.logger.info(f"Sending device data GET request: {url} with params {data}")
            
            response = requests.get(url, params=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info(f"Device data sent successfully to {url}")
                return True
            else:
                self.logger.error(f"Error sending device data: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"HTTP send error: {e}")
            return False
# ==============================================================================
# FILE: cache_manager.py
# ==============================================================================
logger = logging.getLogger(__name__)

class DeviceStatusCache:
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_timeout = TIMEOUT_PENDING_MAINCACHE
            
    def should_filter_message(self, device_name: str, result_data: Dict) -> bool:
        """Checks if a message should be filtered based on cached state."""
        if device_name not in self.cache:
            return False
        
        cached_data = self.cache[device_name]
        
        if time.time() - cached_data['timestamp'] > self.cache_timeout:
            del self.cache[device_name]
            return False
        
        if self._is_data_unchanged(cached_data['data'], result_data):
            logger.debug(f"DEBUG: Cache filtered duplicate - {device_name}")
            return True
        
        return False
    
    def _is_data_unchanged(self, old_data: Dict, new_data: Dict) -> bool:
        """If incomming data matching the Cached value returns True."""
        device_type = new_data.get('type', 'power')
        
        if device_type == 'light_dimmer':
            old_state = old_data.get('avnewstatus')
            new_state = new_data.get('avnewstatus')
            old_brightness = old_data.get('brightness', 0)
            new_brightness = new_data.get('brightness', 0)
            return old_state == new_state and old_brightness == new_brightness
        
        elif device_type == 'power_switch':
            old_state = old_data.get('avnewstatus')
            new_state = new_data.get('avnewstatus')
            return old_state == new_state
        
        elif device_type == 'sensor':
            old_temp = old_data.get('temperature')
            new_temp = new_data.get('temperature')
            old_humidity = old_data.get('humidity')
            new_humidity = new_data.get('humidity')
            old_battery = old_data.get('battery')
            new_battery = new_data.get('battery')
            return (old_temp == new_temp and old_humidity == new_humidity and old_battery == new_battery)

        elif device_type == 'contact':
            old_status = old_data.get('avnewstatus')
            new_status = new_data.get('avnewstatus')
            old_battery = old_data.get('battery')
            new_battery = new_data.get('battery')
            return (old_status == new_status and old_battery == new_battery)
            
        elif device_type == 'motion':
            old_status = old_data.get('avnewstatus')
            new_status = new_data.get('avnewstatus')
            old_battery = old_data.get('battery')
            new_battery = new_data.get('battery')
            old_voltage = old_data.get('voltage')
            new_voltage = new_data.get('voltage')
            return (old_status == new_status and old_battery == new_battery and old_voltage == new_voltage)
        
        else:
            old_state = old_data.get('avnewstatus')
            new_state = new_data.get('avnewstatus')
            old_brightness = old_data.get('brightness', 0)
            new_brightness = new_data.get('brightness', 0)
            return old_state == new_state and old_brightness == new_brightness        

    def update_cache(self, device_name: str, result_data: Dict):
        """Updates the cache with new device data."""
        self.cache[device_name] = {
            'timestamp': time.time(),
            'data': result_data.copy()
        }
        logger.debug(f"DEBUG: Cache updated - {device_name}: {result_data}")
    
    def cleanup_old_entries(self):
        """Cleans up old cache entries."""
        # Placeholder for Future extensions.
        pass
    
# Global instance
device_cache = DeviceStatusCache()

#==============================================================================
# FILE: services.py
# ==============================================================================
class GetResponseCache:
    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_timeout = TIMEOUT_PENDING_GETREQUEST 
            
    def should_send_get_response(self, device_name: str, new_status: Any) -> bool:
        """Checks if a GET response should be sent, avoiding rapid duplicates."""
        if device_name not in self.cache:
            return True
        
        cached_data = self.cache[device_name]
        
        if time.time() - cached_data['timestamp'] > self.cache_timeout:
            del self.cache[device_name]
            return True
        
        if cached_data['status'] == new_status:
            logger.debug(f"DEBUG: GET response cache filtered duplicate - {device_name}: {new_status}")
            return False
        
        return True
    
    def update_get_response_cache(self, device_name: str, new_status: Any):
        """Updates the GET response cache."""
        self.cache[device_name] = {
            'timestamp': time.time(),
            'status': new_status
        }
        logger.debug(f"DEBUG: GET response cache updated - {device_name}: {new_status}")
    
    def cleanup_old_entries(self):
        """Cleans up old entries from the GET response cache."""
        current_time = time.time()
        keys_to_delete = [
            key for key, value in self.cache.items()
            if current_time - value['timestamp'] > self.cache_timeout
        ]
        
        for key in keys_to_delete:
            del self.cache[key]
        
        if keys_to_delete:
            logger.debug(f"DEBUG: GET response cache cleaned up {len(keys_to_delete)} old entries")

# Global GET response cache
get_response_cache = GetResponseCache()

class DeviceStatusManager:
    def __init__(self):
        self.pending_requests = {}  # {device_name: timestamp}
        self.request_timeout = 30   # 30 seconds
    
    def add_request(self, topic: str, payload: dict):
        """Adds a pending GET request."""
        device_name = self._extract_device_name(topic)
        if device_name:
            self.pending_requests[device_name] = time.time()
            logger.debug(f"DEBUG: Added pending request for {device_name}")
    
    def should_send_status(self, topic: str) -> bool:
        """Checks if a status message should be sent for a topic."""
        device_name = self._extract_device_name(topic)
        should_send = device_name in self.pending_requests
        if should_send:
            logger.debug(f"DEBUG: Should send status for {device_name} - pending request found")
        return should_send
    
    def should_send_status_for_device(self, device_name: str) -> bool:
        """Checks if a status message should be sent for a device name."""
        return device_name in self.pending_requests
    
    def mark_request_fulfilled(self, topic: str, result: Dict) -> bool:
        """Marks a request as fulfilled and checks the GET response cache."""
        device_name = self._extract_device_name(topic)
        if device_name in self.pending_requests:
            
            avnewstatus = result.get('avnewstatus')
            device_type = result.get('type')
            
            status_to_cache: Any = avnewstatus
            
            if device_type == 'sensor':
                status_to_cache = f"T={result.get('temperature')}_H={result.get('humidity')}_B={result.get('battery')}"
            elif device_type in ['contact', 'motion']:
                parts = [f"STATUS={avnewstatus}", f"B={result.get('battery')}"]
                if device_type == 'motion':
                    parts.append(f"V={result.get('voltage')}")
                status_to_cache = "_".join(parts)
            
            if get_response_cache.should_send_get_response(device_name, status_to_cache):
                get_response_cache.update_get_response_cache(device_name, status_to_cache)
                del self.pending_requests[device_name]
                logger.debug(f"DEBUG: Request fulfilled and response sent for {device_name}")
                return True
            else:
                del self.pending_requests[device_name]
                logger.debug(f"DEBUG: Request fulfilled but response filtered (duplicate) for {device_name}")
                return False
        
        return False
    
    def cleanup_old_requests(self):
        """Cleans up expired pending requests."""
        current_time = time.time()
        expired = [
            device for device, timestamp in self.pending_requests.items()
            if current_time - timestamp > self.request_timeout
        ]
        for device in expired:
            del self.pending_requests[device]
        if expired:
            logger.debug(f"DEBUG: Cleaned up {len(expired)} expired requests")
    
    def _extract_device_name(self, topic: str) -> str:
        """Extracts device name from topic string."""
        parts = topic.split('/')
        if len(parts) >= 5 and parts[4] in ['l1', 'l2']:
            return f"{parts[3]}/{parts[4]}"  # dual device
        elif len(parts) >= 4:
            return parts[3]  # single device
        return ""

# Global Device Status Manager
device_status_manager = DeviceStatusManager()

def start_background_tasks():
    """Initializes and starts all background cleanup tasks."""
    def cleanup_loop():
        while True:
            time.sleep(300)  # Run every 5 minutes
            device_status_manager.cleanup_old_requests()
            # device_cache.cleanup_old_entries()
            get_response_cache.cleanup_old_entries()
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    logger.info("Background cleanup service started.")
    
    
# ==============================================================================
# FILE: device_processors.py
# ==============================================================================
def process_light_dimmer(topic: str, payload: Dict[str, Any]) -> Optional[Dict]:
    """Process all light/dimmer messages (single, dual, RGB)."""
    try:
        logger.debug(f"DEBUG: Processing light dimmer - Topic: {topic}, Payload: {payload}")
        
        topic_parts = topic.split('/')
        
        if topic_parts[-1] == 'set':
            logger.debug(f"DEBUG: Skipping /set topic: {topic}")
            return None
        
        if len(topic_parts) == 4 and 'brightness_l1' in payload and 'brightness_l2' in payload:
            logger.debug(f"DEBUG: Skipping main dual dimmer device - Topic: {topic}")
            return None
        
        room = topic_parts[2]
        device_name = topic_parts[3]
        
        endpoint = ""
        if len(topic_parts) >= 5 and topic_parts[4] in ['l1', 'l2']:
            endpoint = topic_parts[4]
            avdevicename = f"{device_name}/{endpoint}"
        else:
            avdevicename = device_name
        
        state = payload.get('state', '')
        brightness = payload.get('brightness', 0)
        
        avnewstatus = 'OFF'
        if isinstance(state, str):
            avnewstatus = 'ON' if state.upper() == 'ON' else 'OFF'
        elif isinstance(state, bool):
            avnewstatus = 'ON' if state else 'OFF'
        elif isinstance(state, int):
            avnewstatus = 'ON' if state > 0 else 'OFF'

        color_data = "not_supported"
        if 'color' in payload:
            color = payload['color']
            if isinstance(color, dict):
                if 'x' in color and 'y' in color:
                    color_data = f"x={color['x']},y={color['y']}"
                elif 'r' in color and 'g' in color and 'b' in color:
                    color_data = f"r={color['r']},g={color['g']},b={color['b']}"
        
        result = {
            'room': room,
            'avdevicename': avdevicename,
            'avnewstatus': avnewstatus,
            'type': 'light_dimmer',
            'state': avnewstatus,
            'brightness': brightness,
            'color': color_data
        }
        
        logger.debug(f"DEBUG: Light dimmer result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing light dimmer {topic}: {e}")
        return None

def process_power_switch(topic: str, payload: Any) -> Optional[Union[Dict, List[Dict]]]:
    """Process all switch messages."""
    logger.debug(f"POWER SWITCH DEBUG: Topic: {topic}, Payload: {payload}")
    
    if not isinstance(topic, str): return None
    
    topic_parts = topic.split('/')
    if len(topic_parts) < 4 or topic_parts[0] != "gtl": return None
    
    if topic_parts[-1] == 'set':
        logger.debug(f"DEBUG: Skipping /set topic: {topic}")
        return None
    
    if not isinstance(payload, dict): return None
    
    room = topic_parts[2]
    device_name = topic_parts[3]
    results = []
    
    if 'state' in payload:
        state = payload['state']
        avnewstatus = "ON" if state == "ON" else "OFF"
        results.append({
            'room': room, 'avdevicename': device_name, 'avnewstatus': avnewstatus,
            'type': 'power_switch', 'state': avnewstatus
        })
    
    if 'state_l1' in payload:
        state_l1 = payload['state_l1']
        avnewstatus_l1 = "ON" if state_l1 == "ON" else "OFF"
        results.append({
            'room': room, 'avdevicename': f"{device_name}/l1", 'avnewstatus': avnewstatus_l1,
            'type': 'power_switch', 'state': avnewstatus_l1
        })
    
    if 'state_l2' in payload:
        state_l2 = payload['state_l2']
        avnewstatus_l2 = "ON" if state_l2 == "ON" else "OFF"
        results.append({
            'room': room, 'avdevicename': f"{device_name}/l2", 'avnewstatus': avnewstatus_l2,
            'type': 'power_switch', 'state': avnewstatus_l2
        })
    
    logger.debug(f"POWER SWITCH DEBUG: Result: {results}")
    
    if len(results) == 1: return results[0]
    if len(results) > 1: return results
    return None

def process_sensor_data(topic: str, payload: Any) -> Optional[Dict]:
    """Processes sensor data messages."""
    if not isinstance(topic, str): return None
    
    topic_parts = topic.split('/')
    if len(topic_parts) < 3 or topic_parts[0] != "gtl": return None
    
    if not isinstance(payload, dict): return None
    
    room = topic_parts[2]
    avdevicename = topic_parts[3]
    
    if 'humidity' in payload or 'temperature' in payload:
        return {
            'room': room, 'avdevicename': avdevicename, 'type': 'sensor',
            'humidity': payload.get('humidity'), 'temperature': payload.get('temperature'),
            'battery': payload.get('battery')
        }
    
    if 'contact' in payload:
        status_contact = "Zárva" if payload['contact'] else "Nyitva"
        return {
            'room': room, 'avdevicename': avdevicename, 'type': 'contact',
            'avnewstatus': status_contact, 'battery': payload.get('battery')
        }
    
    if 'occupancy' in payload:
        status_motion = "detected" if payload['occupancy'] else "cleared"
        return {
            'room': room, 'avdevicename': avdevicename, 'type': 'motion',
            'avnewstatus': status_motion, 'battery': payload.get('battery'),
            'voltage': payload.get('voltage')
        }
    
    return None

# ==============================================================================
# FILE: device_list_processor.py
# ==============================================================================
def _extract_device_parameters(device: dict, endpoints: list) -> Dict[str, Any]:
    """Extract device-specific parameters based on device type and features"""
    parameters = {}
    
    simple_keys = ['state', 'brightness', 'color', 'temperature', 'humidity', 'pressure', 'illuminance',
                   'contact', 'occupancy', 'battery', 'voltage', 'power', 'energy', 'current',
                   'state_l1', 'state_l2', 'brightness_l1', 'brightness_l2']
    for key in simple_keys:
        if device.get(key) is not None:
            parameters[key] = device.get(key)
    
    if device.get('definition') and device['definition'].get('exposes'):
        for expose in device['definition']['exposes']:
            if (expose.get('property') == 'color' or expose.get('name') == 'color_xy' or
                (expose.get('features') and any(f.get('name') and 'color' in f['name'] for f in expose['features']))):
                parameters['rgb_supported'] = True
            if expose.get('property') == 'color_temp':
                parameters['color_temp_supported'] = True
                if device.get('color_temp') is not None:
                     parameters['color_temp'] = device.get('color_temp')
            if expose.get('property') == 'color_mode':
                parameters['color_mode'] = device.get('color_mode')
    
    return parameters

def _map_device_type(zigbee_type: str, device_data: dict, device_parameters: dict) -> str:
    """Map Zigbee device type to simplified types with enhanced detection"""
    if device_parameters.get('rgb_supported'): return 'rgb_light'
    if device_parameters.get('brightness') is not None: return 'dimmer'
    if device_parameters.get('state') is not None: return 'switch'
    if any(k in device_parameters for k in ['temperature', 'humidity']): return 'temperature_sensor'
    if 'contact' in device_parameters: return 'contact_sensor'
    if 'occupancy' in device_parameters: return 'motion_sensor'
    if any(k in device_parameters for k in ['power', 'energy']): return 'smart_plug'
    return 'sensor' if zigbee_type == 'EndDevice' else 'switch'

def process_device_list(payload: Any, topic: str) -> Optional[Dict]:
    """Processes the full device list from zigbee2mqtt."""
    if not isinstance(payload, list): return None
    
    devices, discovered_rooms = [], set()
    
    for device in payload:
        if not isinstance(device, dict) or not device.get('friendly_name') or not device.get('supported'):
            continue
        
        match = re.match(r'^([^\/]+)\/([^\/]+)\/(.+)$', device['friendly_name'])
        if not match: continue
        
        room, device_name = match.group(2), match.group(3)
        discovered_rooms.add(room)
        
        endpoints = [
            {'endpoint': e['endpoint'], 'type': e.get('type', 'unknown'),
             'features': [f.get('name') or f.get('property') for f in e['features']]}
            for e in device.get('definition', {}).get('exposes', []) if e.get('endpoint') and e.get('features')
        ]
        
        device_parameters = _extract_device_parameters(device, endpoints)
        device_type = _map_device_type(device.get('type', 'Router'), device, device_parameters)
        
        devices.append({
            'room': room, 'name': device['friendly_name'], 'device_type': device_type,
            'zigbee_type': device.get('type', 'Router'), 'parameters': device_parameters,
            'endpoints': endpoints, 'endpoint_count': len(endpoints), 'is_main_device': True
        })

    update_allowed_rooms(list(discovered_rooms))
    
    summary = {
        'by_room': {r: sum(1 for d in devices if d['room'] == r) for r in discovered_rooms},
        'by_device_type': {t: sum(1 for d in devices if d['device_type'] == t) for t in set(d['device_type'] for d in devices)},
        'rooms': list(discovered_rooms)
    }

    result_data = {
        'timestamp': datetime.now().isoformat(), 'devices': devices,
        'total_devices': len(devices), 'summary': summary,
    }
    
    return result_data

# ==============================================================================
# FILE: message_router.py
# ==============================================================================
def _get_topic_type(topic: str, payload: Any) -> str:
    """Determines the type of message based on topic and payload."""
    if not isinstance(topic, str): return "invalid_topic"
    
    if topic in [f"{MQTT_TOPIC}/bridge/devices", "usb/bridge/devices"]: return "device_list"
    if f'{MQTT_TOPIC}/bridge/info' in topic: return "logging_filtered"
    
    topic_parts = topic.split('/')
    if topic_parts[0] != MQTT_TOPIC: return "not_gtl_topic"
    
    if topic.endswith('/get') and isinstance(payload, dict): return "device_status_request"
    if (topic.endswith('/set') or 'state' in payload or 'brightness' in payload) and device_status_manager.should_send_status(topic):
        return "device_status_send"
    
    if isinstance(payload, dict):
        if any(k in payload for k in ['brightness', 'brightness_l1', 'brightness_l2']): return "light_dimmer"
        if any(k in payload for k in ['state', 'state_l1', 'state_l2']): return "power_switch"
        if any(k in payload for k in ['humidity', 'temperature', 'contact', 'occupancy']): return "sensor_data"
    
    return "unknown"

def _process_device_status_send(topic: str, payload: Any) -> Optional[Dict]:
    """Handles status updates that are responses to a pending GET request."""
    logger.debug(f"DEBUG: Device status send - Topic: {topic}")
    
    result = None
    if isinstance(payload, dict):
        if any(k in payload for k in ['brightness', 'brightness_l1', 'brightness_l2']):
            result = process_light_dimmer(topic, payload)
        elif any(k in payload for k in ['state', 'state_l1', 'state_l2']):
            raw_result = process_power_switch(topic, payload)
            result = raw_result[0] if isinstance(raw_result, list) and raw_result else raw_result
        elif any(k in payload for k in ['humidity', 'temperature', 'contact', 'occupancy']):
            result = process_sensor_data(topic, payload)
    
    if isinstance(result, dict):
        if device_status_manager.mark_request_fulfilled(topic, result):
            logger.debug(f"DEBUG: Status sent for pending request - Device: {result.get('avdevicename', 'unknown')}")
            return result
        else:
            logger.debug(f"DEBUG: Status filtered by GET response cache - Device: {result.get('avdevicename', 'unknown')}")
            return None
    return None

def route_message(topic: str, payload: Any) -> Optional[Union[Dict, List[Dict]]]:
    """Main message processing and routing function."""
    try:
        topic_type = _get_topic_type(topic, payload)
        logger.debug(f"DEBUG: Topic: {topic}, Detected type: {topic_type}")

        if topic_type == "device_list":
            result = process_device_list(payload, topic)
            if result: save_z2mqtt_data(result)
            return result
        
        if topic_type == "device_status_request":
            device_status_manager.add_request(topic, payload)
            return None
        
        if topic_type == "device_status_send":
            return _process_device_status_send(topic, payload)

        processors = {
            "light_dimmer": process_light_dimmer,
            "power_switch": process_power_switch,
            "sensor_data": process_sensor_data
        }
        
        processor = processors.get(topic_type)
        if not processor:
            logger.debug(f"DEBUG: Unknown or filtered topic type: {topic_type}")
            return None
        
        raw_result = processor(topic, payload)
        if not raw_result: return None

        results = raw_result if isinstance(raw_result, list) else [raw_result]
        final_results = []

        for result in results:
            if isinstance(result, dict) and 'avdevicename' in result:
                device_name = result['avdevicename']
                if not device_cache.should_filter_message(device_name, result):
                    device_cache.update_cache(device_name, result)
                    final_results.append(result)

        if not final_results: return None
        return final_results[0] if len(final_results) == 1 else final_results
            
    except Exception as e:
        logger.error(f"Processing error for topic {topic}: {e}", exc_info=True)
        return None


# ==============================================================================
# FILE: mqtt_handler.py
# ==============================================================================
class MQTTHandler:
    def __init__(self, broker, port, username=None, password=None):
        self.broker = broker
        self.port = port
        self.http_client = HTTPClient()
        self.logger = logging.getLogger(__name__)
        
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        if username and password:
            self.client.username_pw_set(username, password)
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info(f"Successfully connected to MQTT: {self.broker}:{self.port}")
            client.subscribe(f"{MQTT_TOPIC}/#")
            client.subscribe("client/con_ip")
        else:
            self.logger.error(f"Failed to connect, return code {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode('utf-8')
            self.logger.info(f"Message received: {msg.topic}")

            if msg.topic == "client/con_ip":
                ip_client.update_ip_from_message(msg.topic, payload_str)
                return

            try:
                payload = json.loads(payload_str) if payload_str else {}
            except json.JSONDecodeError:
                self.logger.warning(f"JSON decode error on topic {msg.topic}, payload: '{payload_str}'")
                return

            processed_data = route_message(msg.topic, payload)
            
            if processed_data:
                if msg.topic == f"{MQTT_TOPIC}/bridge/devices" or msg.topic == "usb/bridge/devices":
                    self.http_client.send_z2mqtt_data(processed_data, HTTP_DATA_PORT)
                elif isinstance(processed_data, list):
                    for item in processed_data:
                         self.http_client.send_device_data(item, HTTP_DEVICE_PORT)
                else:
                    self.http_client.send_device_data(processed_data, HTTP_DEVICE_PORT)
                    
        except Exception as e:
            self.logger.error(f"Error processing message from topic {msg.topic}: {e}", exc_info=True)
    
    def start(self):
        try:
            self.logger.info(f"Connecting to broker at {self.broker}:{self.port}")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_forever()
        except Exception as e:
            self.logger.critical(f"MQTT client failed to start: {e}", exc_info=True)


# ==============================================================================
# FILE: main.py
# ==============================================================================
def main():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Z2MQTT to HTTP Bridge...")
    
    try:
        start_background_tasks()
        
        handler = MQTTHandler(
            broker=MQTT_BROKER,
            port=MQTT_PORT,
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD
        )
        handler.start()
    except KeyboardInterrupt:
        logger.info("Application shutting down.")
    except Exception as e:
        logger.critical(f"An unhandled error occurred in main: {e}", exc_info=True)

if __name__ == "__main__":
    main()