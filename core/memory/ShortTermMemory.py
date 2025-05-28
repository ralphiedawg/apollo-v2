from collections import deque
from datetime import datetime

class ShortTermMemory:
    def __init__(self, max_entries=15):
        self.max_entries = max_entries
        self.buffer = deque(maxlen=max_entries)

    def remember(self, user_input, apollo_response):
        self.buffer.append({
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "response": apollo_response
        })

    def get_context(self):
        return list(self.buffer)

