import time
from typing import Dict, Any
from config import TIMEOUT_PENDING_GETREQUEST

class GetResponseCache:
    def __init__(self):
        self.cache: Dict[str, dict] = {}
        self.timeout = TIMEOUT_PENDING_GETREQUEST 
            
    def should_send(self, device_name: str, status: Any) -> bool:
        if device_name not in self.cache: return True
        cached = self.cache[device_name]
        if time.time() - cached['timestamp'] > self.timeout: return True
        return str(cached['status']) != str(status)
    
    def update(self, device_name: str, status: Any):
        self.cache[device_name] = {'timestamp': time.time(), 'status': status}

    def cleanup(self):
        now = time.time()
        expired = [k for k, v in self.cache.items() if now - v['timestamp'] > self.timeout]
        for k in expired: del self.cache[k]

get_response_cache = GetResponseCache()

class DeviceStatusManager:
    def __init__(self):
        self.pending = {} 
    
    def add(self, topic: str):
        name = self._extract(topic)
        if name: self.pending[name] = time.time()
    
    def is_pending(self, topic: str) -> bool:
        return self._extract(topic) in self.pending
    
    def fulfill(self, topic: str):
        name = self._extract(topic)
        if name in self.pending: del self.pending[name]

    def cleanup(self):
        now = time.time()
        expired = [k for k, v in self.pending.items() if now - v > 30]
        for k in expired: del self.pending[k]

    def _extract(self, topic: str) -> str:
        parts = topic.split('/')
        if len(parts) >= 5 and parts[4] in ['l1', 'l2']: return f"{parts[3]}/{parts[4]}"
        return parts[3] if len(parts) >= 4 else ""

device_status_manager = DeviceStatusManager()

