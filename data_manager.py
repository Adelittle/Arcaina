import json
import os
from datetime import datetime

class DataManager:
    def __init__(self, filepath='stats.json', on_save_callback=None):
        self.filepath = filepath
        self.data = self._load()
        self.on_save_callback = on_save_callback

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        return self._get_default_stats()
                    return json.loads(content)
            except (json.JSONDecodeError, ValueError):
                return self._get_default_stats()
        return self._get_default_stats()

    def _get_default_stats(self):
        return {
            "user_stats": {
                "exp": 0,
                "level": 0,
                "total_logins": 0,
                "last_login": None,
                "streak": 0,
                "current_week_start": datetime.now().strftime('%Y-%m-%d'),
                "days_logged_this_week": 0,
                "start_date": datetime.now().isoformat()
            },
            "history": []
        }

    def save(self, message=None):
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=4)
        
        # Trigger Auto Backup callback (e.g., Telegram)
        if self.on_save_callback:
            try:
                self.on_save_callback(self.filepath, message)
            except Exception as e:
                print(f"Backup Callback Error: {e}")

    def get_stats(self):
        return self.data["user_stats"]

    def add_history(self, event_type, exp_gained, metadata=None, message=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "exp_gained": exp_gained,
            "metadata": metadata or {}
        }
        self.data["history"].append(entry)
        self.save(message=message)

    def update_stats(self, message=None, **kwargs):
        for key, value in kwargs.items():
            if key in self.data["user_stats"]:
                self.data["user_stats"][key] = value
        self.save(message=message)
