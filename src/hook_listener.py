import json
import os
from pynput import mouse
from src.session_sync import SessionManager

class HookListener:
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.events = []
        self.listener = None
        self.session = SessionManager()

    def on_click(self, x, y, button, pressed):
        # We record both left and right mouse down
        if pressed and button in (mouse.Button.left, mouse.Button.right):
            timestamp = self.session.get_timestamp()
            # Only record if the session is active
            if self.session.is_recording:
                self.events.append({
                    "timestamp": timestamp,
                    "x": int(x),
                    "y": int(y),
                    "button": "left" if button == mouse.Button.left else "right"
                })

    def start(self):
        self.events = []
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
        self.save()

    def save(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
        with open(self.log_path, 'w') as f:
            json.dump(self.events, f, indent=4)
