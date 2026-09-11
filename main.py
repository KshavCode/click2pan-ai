import json
import time
import os
import threading
from pynput import keyboard
from src.hook_listener import HookListener
from src.recorder import ScreenRecorder
from src.event_processor import EventProcessor
from src.renderer import Renderer
from src.gui import AutoEditGUI

def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return json.load(f)

class Orchestrator:
    def __init__(self):
        self.config = load_config("config.json")
        paths = self.config["paths"]
        self.raw_video = os.path.join(paths["workspace"], paths["raw_video"])
        self.events_log = os.path.join(paths["workspace"], paths["events_log"])
        self.final_output = os.path.join(paths["workspace"], paths["final_output"])
        
        self.recorder = ScreenRecorder(
            output_path=self.raw_video,
            fps=self.config["video_settings"]["fps"],
            audio_device=self.config.get("app_settings", {}).get("audio_device", "")
        )
        self.listener = HookListener(log_path=self.events_log)
        self.event_processor = EventProcessor(self.config)
        self.renderer = Renderer(self.config)
        
        self.is_recording = False
        self.lock = threading.Lock()
        
        self.gui = AutoEditGUI(self)
        self.hotkey_listener = None
        self.update_hotkey(self.config.get("app_settings", {}).get("hotkey", "<ctrl>+<shift>+r"))

    def update_hotkey(self, hotkey_str):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        self.hotkey_listener = keyboard.GlobalHotKeys({
            hotkey_str: self.toggle_recording
        })
        self.hotkey_listener.start()

    def toggle_recording(self):
        with self.lock:
            if not self.is_recording:
                print("Starting recording...")
                # Hide GUI on main thread
                self.gui.after(0, self.gui.withdraw)
                
                self.listener.start()
                self.recorder.start()
                self.is_recording = True
                print("Recording started.")
            else:
                print("Stopping recording...")
                self.recorder.stop()
                self.listener.stop()
                self.is_recording = False
                print("Recording stopped. Processing events...")
                
                # Show GUI again
                self.gui.after(0, self.gui.deiconify)
                self.gui.after(0, self.gui.show_rendering_progress)
                
                # Process the recorded events in a separate thread to not freeze GUI
                threading.Thread(target=self.process_and_render, daemon=True).start()

    def process_and_render(self):
        try:
            if not os.path.exists(self.events_log):
                print("No events log found. Skipping render.")
                self.gui.after(0, self.gui.hide_rendering_progress)
                return
                
            with open(self.events_log, 'r') as f:
                raw_events = json.load(f)
                
            processed_events = self.event_processor.process_raw_events(raw_events)
            
            self.renderer.render(
                self.raw_video, 
                processed_events, 
                self.final_output,
                progress_callback=self.gui.update_progress
            )
            print("Done! Check workspace/final_edit.mp4")
        finally:
            self.gui.after(0, self.gui.hide_rendering_progress)

    def run(self):
        self.gui.mainloop()

if __name__ == "__main__":
    app = Orchestrator()
    app.run()