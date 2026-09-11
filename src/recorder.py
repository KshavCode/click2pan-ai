import subprocess
import os
import imageio_ffmpeg
from src.session_sync import SessionManager

class ScreenRecorder:
    def __init__(self, output_path: str, fps: int = 60, audio_device: str = ""):
        self.output_path = output_path
        self.fps = fps
        self.audio_device = audio_device
        self.process = None
        self.session = SessionManager()
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def start(self):
        # Ensure output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
        
        # Command for FFmpeg to record Windows desktop using gdigrab
        # -r 60 ensures constant framerate
        cmd = [
            self.ffmpeg_exe,
            '-y',  # Overwrite output
            '-f', 'gdigrab',
            '-framerate', str(self.fps),
            '-i', 'desktop'
        ]
        
        # Add audio device if specified
        if self.audio_device:
            cmd.extend([
                '-f', 'dshow',
                '-i', f'audio={self.audio_device}'
            ])
            
        # Encoding parameters
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '18',
            '-pix_fmt', 'yuv420p',
            '-r', str(self.fps)
        ])
        
        if self.audio_device:
            cmd.extend(['-c:a', 'aac', '-b:a', '192k'])

        cmd.append(self.output_path)
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Start session clock immediately after launching ffmpeg
        self.session.start_session()

    def stop(self):
        if self.process:
            # Send 'q' to ffmpeg to stop recording gracefully
            try:
                self.process.communicate(b'q\n', timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
            self.process.wait()
        
        self.session.stop_session()
