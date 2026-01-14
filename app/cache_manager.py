
import time
from typing import Dict
from config import TIMEOUT_PENDING_MAINCACHE

class DeviceStatusCache:
    def __init__(self):
        self.cache: Dict[str, dict] = {}
        self.timeout = TIMEOUT_PENDING_MAINCACHE
            
    def should_filter_message(self, device_name: str, result_data: dict) -> bool:
        if device_name not in self.cache: 
            return False
            
        cached = self.cache[device_name]
        # Force Sync
        if time.time() - cached['timestamp'] > self.timeout: 
            return False
        
        old_data = cached['data']
        
        # Extract vaalues
        exact_keys = ['avnewstatus', 'brightness', 'battery', 'contact', 'occupancy']
        for target_value in exact_keys:
            if target_value in result_data and result_data.get(target_value) != old_data.get(target_value):
                return False # Változott, ne szűrd (küldd el)

        # 2. Filter 
        analog_keys = ['temperature', 'humidity']
        for target_value in analog_keys:
            if target_value in result_data:
                new_val = result_data.get(target_value)
                old_val = old_data.get(target_value)
                
                if new_val is not None and old_val is not None:
                    # (int(float(...))) I Keep what i need, only full integer changes
                    if int(float(new_val)) != int(float(old_val)):
                        return False 
                elif new_val != old_val:
                    return False

        return True # drop everything whats left

    def update(self, device_name: str, result_data: dict):
        # save last data
        self.cache[device_name] = {'timestamp': time.time(), 'data': result_data.copy()}

device_cache = DeviceStatusCache()