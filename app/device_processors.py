import logging
from typing import Dict, Any, Optional, Union, List

logger = logging.getLogger(__name__)

def process_light_dimmer(topic: str, payload: Dict[str, Any]) -> Optional[Union[Dict, List[Dict]]]:
    # only if "brightness" is present 
    try:
        topic_parts = topic.split('/')
        if len(topic_parts) < 4 or topic_parts[-1] == 'set':
            return None
        
        room = topic_parts[2]
        device_name = topic_parts[3]
        results = []

        # Dual Dimmer ellenőrzése (L1/L2)
        has_l1_l2 = any(k in payload for k in ['state_l1', 'state_l2', 'brightness_l1', 'brightness_l2'])

        if has_l1_l2:
            for ep in ['l1', 'l2']:
                s_key, b_key = f'state_{ep}', f'brightness_{ep}'
                if s_key in payload or b_key in payload:
                    state = payload.get(s_key, 'OFF')
                    results.append({
                        'room': room,
                        'avdevicename': f"{device_name}/{ep}",
                        'avnewstatus': 'ON' if str(state).upper() == 'ON' else 'OFF',
                        'type': 'light_dimmer',
                        'brightness': payload.get(b_key, 0)
                    })
        else:
            # Single dimmer
            if 'brightness' in payload or 'state' in payload:
                state = payload.get('state', 'OFF')
                # Topic based recognition to handle  
                ep_suffix = topic_parts[4] if len(topic_parts) >= 5 and topic_parts[4] in ['l1', 'l2'] else ""
                dev_name = f"{device_name}/{ep_suffix}" if ep_suffix else device_name
                
                results.append({
                    'room': room,
                    'avdevicename': dev_name,
                    'avnewstatus': 'ON' if str(state).upper() == 'ON' else 'OFF',
                    'type': 'light_dimmer',
                    'brightness': payload.get('brightness', 0)
                })

        return results[0] if len(results) == 1 else (results if results else None)
    except Exception as e:
        logger.error(f"Hiba a process_light_dimmer-ben: {e}")
        return None

def process_power_switch(topic: str, payload: Any) -> Optional[Union[Dict, List[Dict]]]:
    # wihthout "brightness"
    if not isinstance(payload, dict):
        return None
    
    topic_parts = topic.split('/')
    if len(topic_parts) < 4 or topic_parts[-1] == 'set':
        return None
    
    room = topic_parts[2]
    device_name = topic_parts[3]
    results = []
    
    # to recognize some other dual devices type status changes  (state, state_l1, state_l2)
    for key, suffix in [('state', ''), ('state_l1', '/l1'), ('state_l2', '/l2')]:
        if key in payload:
            status = "ON" if str(payload[key]).upper() == "ON" else "OFF"
            results.append({
                'room': room, 
                'avdevicename': f"{device_name}{suffix}", 
                'avnewstatus': status, 
                'type': 'power_switch'
            })
    
    if len(results) == 1:
        return results[0]
    return results if results else None

def process_sensor_data(topic: str, payload: Any) -> Optional[Dict]:
    # sensor
    if not isinstance(payload, dict):
        return None
    
    topic_parts = topic.split('/')
    if len(topic_parts) < 4:
        return None
    
    room, device_name = topic_parts[2], topic_parts[3]
    
    # Hőmérséklet/Páratartalom
    if 'humidity' in payload or 'temperature' in payload:
        return {
            'room': room, 'avdevicename': device_name, 'type': 'sensor',
            'humidity': payload.get('humidity'), 'temperature': payload.get('temperature'),
            'battery': payload.get('battery')
        }
    
    # Nyitásérzékelő
    if 'contact' in payload:
        return {
            'room': room, 'avdevicename': device_name, 'type': 'contact',
            'avnewstatus': "Zárva" if payload['contact'] else "Nyitva", 'battery': payload.get('battery')
        }
    
    # Mozgásérzékelő
    if 'occupancy' in payload:
        return {
            'room': room, 'avdevicename': device_name, 'type': 'motion',
            'avnewstatus': "detected" if payload['occupancy'] else "cleared", 
            'battery': payload.get('battery'), 'voltage': payload.get('voltage')
        }
    
    return None