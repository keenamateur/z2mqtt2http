import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from config import update_allowed_rooms, logger

def _extract_device_parameters(device: dict, endpoints: list) -> Dict[str, Any]:
    # Extract device parameters
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
    """Map Zigbee device type to simplified types with enhanced detection (ORIGINAL LOGIC)"""
    if device_parameters.get('rgb_supported'): return 'rgb_light'
    if device_parameters.get('brightness') is not None: return 'dimmer'
    if device_parameters.get('state') is not None: return 'switch'
    if any(k in device_parameters for k in ['temperature', 'humidity']): return 'temperature_sensor'
    if 'contact' in device_parameters: return 'contact_sensor'
    if 'occupancy' in device_parameters: return 'motion_sensor'
    if any(k in device_parameters for k in ['power', 'energy']): return 'smart_plug'
    return 'sensor' if zigbee_type == 'EndDevice' else 'switch'

def process_device_list(payload: Any, topic: str) -> Optional[Dict[str, Any]]:
    # to match tasker preferences
    if not isinstance(payload, list):
        return None
    
    devices = []
    discovered_rooms = set()
    
    for device in payload:
        # keep only recognized devices
        if not isinstance(device, dict) or not device.get('friendly_name') or not device.get('supported'):
            continue
            
        # Friendly name : gtl/szoba/eszkoznev  topic/room/devicename
        friendly_name = device['friendly_name']
        match = re.match(r'^([^\/]+)\/([^\/]+)\/(.+)$', friendly_name)
        
        if match:
            room = match.group(2)
            discovered_rooms.add(room)
            
            # Get Endpoints 
            endpoints = []
            if device.get('definition') and device['definition'].get('exposes'):
                endpoints = [
                    {
                        'endpoint': e.get('endpoint'), 
                        'type': e.get('type', 'unknown'),
                        'features': [f.get('name') or f.get('property') for f in e.get('features', [])]
                    }
                    for e in device['definition']['exposes'] if e.get('endpoint') and e.get('features')
                ]
            
            device_parameters = _extract_device_parameters(device, endpoints)
            device_type = _map_device_type(device.get('type', 'Router'), device, device_parameters)
            
            # set data 
            dev_data = {
                'room': room,
                'name': friendly_name, 
                'device_type': device_type,
                'zigbee_type': device.get('type', 'Router'),
                'parameters': device_parameters,
                'endpoints': endpoints,
                'endpoint_count': len(endpoints),
                'is_main_device': True
            }
            devices.append(dev_data)
        else:
            # Controlled devices without matching name preferenc
            logger.debug(f"Device skipped or partially processed (regex mismatch): {friendly_name}")

    if discovered_rooms:
        update_allowed_rooms(list(discovered_rooms))
    
    # device summary 
    summary = {
        'by_room': {r: sum(1 for d in devices if d['room'] == r) for r in discovered_rooms},
        'by_device_type': {t: sum(1 for d in devices if d['device_type'] == t) for t in set(d['device_type'] for d in devices)},
        'rooms': list(discovered_rooms)
    }

    # json
    result_data = {
        'timestamp': datetime.now().isoformat(),
        'devices': devices,
        'total_devices': len(devices),
        'summary': summary
    }
    
    return result_data