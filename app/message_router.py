from typing import Dict, Any, Optional, Union, List
from config import MQTT_TOPIC, logger
from cache_manager import device_cache
from services import device_status_manager, get_response_cache
from device_processors import process_light_dimmer, process_power_switch, process_sensor_data
from device_list_processor import process_device_list

def route_message(topic: str, payload: Any) -> tuple[Optional[Union[Dict, List]], bool]:
    try:
        # 1. Device List
        if topic.endswith('bridge/devices') or topic == "usb/bridge/devices":
            return process_device_list(payload, topic), True

        # 2. GET Request
        if topic.endswith('/get'):
            device_status_manager.add(topic)
            return None, False

        # 3. Adatfeldolgozás meghatározása
        result = None
        if isinstance(payload, dict):
            # Van fényerő adat? -> Dimmer
            if any(k in payload for k in ['brightness', 'brightness_l1', 'brightness_l2']):
                result = process_light_dimmer(topic, payload)
            
            # Nincs fényerő, de van állapot? -> Switch
            elif any(k in payload for k in ['state', 'state_l1', 'state_l2']):
                result = process_power_switch(topic, payload)
            
            # Egyéb szenzor?
            elif any(k in payload for k in ['humidity', 'temperature', 'contact', 'occupancy']):
                result = process_sensor_data(topic, payload)

        if not result:
            return None, False
        
        # Iterálható formátum (Dual eszközök tÖbB  elemet adhatnak vissza)
        results = result if isinstance(result, list) else [result]
        final_list = []
        is_manual = device_status_manager.is_pending(topic)

        for item in results:
            dev_name = str(item.get('avdevicename', ''))
            if not dev_name: 
                continue

            if is_manual:
                # Manuális GET kérés: Cache bypass, GetCache duplikáció szűrés
                status_val = str(item.get('avnewstatus', ''))
                if get_response_cache.should_send(dev_name, status_val):
                    get_response_cache.update(dev_name, status_val)
                    final_list.append(item)
                device_status_manager.fulfill(topic)
            else:
                # Automatikus jelentés: SZŰRÉS A fő cache alapján
                if not device_cache.should_filter_message(dev_name, item):
                    device_cache.update(dev_name, item)
                    final_list.append(item)
        
        if not final_list:
            return None, False
            
        return (final_list[0] if len(final_list) == 1 else final_list), False

    except Exception as e:
        logger.error(f"Router hiba topic-nál ({topic}): {e}")
        return None, False