import customtkinter as ctk
import json
import threading
import subprocess
import imageio_ffmpeg
import re
from tkinter import messagebox

class AutoEditGUI(ctk.CTk):
    def __init__(self, orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.config = self.orchestrator.config
        
        self.title("AutoEdit - Smart Screen Recorder")
        self.geometry("450x350")
        self.resizable(False, False)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # UI Elements
        self.lbl_title = ctk.CTkLabel(self, text="AutoEdit Dashboard", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.pack(pady=(20, 10))

        # Audio Device Selector
        self.lbl_audio = ctk.CTkLabel(self, text="Select Microphone:")
        self.lbl_audio.pack(anchor="w", padx=40)
        
        self.audio_combo = ctk.CTkComboBox(self, width=370, values=["Searching..."])
        self.audio_combo.pack(padx=40, pady=(0, 15))
        
        # Hotkey Configuration
        self.lbl_hotkey = ctk.CTkLabel(self, text="Start/Stop Hotkey:")
        self.lbl_hotkey.pack(anchor="w", padx=40)
        
        self.hotkey_entry = ctk.CTkEntry(self, width=370)
        self.hotkey_entry.insert(0, self.config.get("app_settings", {}).get("hotkey", "<ctrl>+<shift>+r"))
        self.hotkey_entry.pack(padx=40, pady=(0, 20))
        
        # Save Config Button
        self.btn_save = ctk.CTkButton(self, text="Save Settings & Register Hotkey", command=self.save_settings)
        self.btn_save.pack(pady=5)
        
        # Progress UI
        self.status_var = ctk.StringVar(value="Status: Ready")
        self.lbl_status = ctk.CTkLabel(self, textvariable=self.status_var, text_color="gray")
        self.lbl_status.pack(pady=(10, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self, width=370)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)
        self.progress_bar.pack_forget() # Hidden initially
        
        # Start background task to fetch audio devices
        threading.Thread(target=self.fetch_audio_devices, daemon=True).start()

    def fetch_audio_devices(self):
        try:
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            res = subprocess.run([exe, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'], 
                               capture_output=True, text=True, errors='ignore')
            lines = res.stderr.splitlines()
            audio_devices = ["None (No Audio)"]
            in_audio = False
            for line in lines:
                if 'DirectShow audio devices' in line:
                    in_audio = True
                elif 'DirectShow video devices' in line:
                    in_audio = False
                elif in_audio and ']' in line and 'Alternative name' not in line:
                    match = re.search(r'\"([^\"]+)\"', line)
                    if match:
                        audio_devices.append(match.group(1))
                        
            # Update GUI safely
            self.after(0, self._update_audio_combo, audio_devices)
        except Exception as e:
            self.after(0, self._update_audio_combo, ["None (No Audio)"])

    def _update_audio_combo(self, devices):
        self.audio_combo.configure(values=devices)
        current = self.config.get("app_settings", {}).get("audio_device", "")
        if current in devices:
            self.audio_combo.set(current)
        else:
            self.audio_combo.set(devices[0])

    def save_settings(self):
        hotkey = self.hotkey_entry.get()
        audio = self.audio_combo.get()
        if audio == "None (No Audio)":
            audio = ""
            
        if "app_settings" not in self.config:
            self.config["app_settings"] = {}
            
        self.config["app_settings"]["hotkey"] = hotkey
        self.config["app_settings"]["audio_device"] = audio
        
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=4)
            
        # Update orchestrator
        self.orchestrator.recorder.audio_device = audio
        self.orchestrator.update_hotkey(hotkey)
        self.status_var.set("Status: Settings Saved. Ready to record.")
        messagebox.showinfo("Success", "Settings saved and hotkey registered!")

    def show_rendering_progress(self):
        self.status_var.set("Status: Rendering Video...")
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
    def update_progress(self, value):
        self.after(0, self.progress_bar.set, value)
        
    def hide_rendering_progress(self):
        self.progress_bar.pack_forget()
        self.status_var.set("Status: Render Complete. Ready.")
