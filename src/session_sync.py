import time
import threading

class SessionManager:
    """
    Thread-safe singleton to manage the recording timeline.
    Ensures video capture and mouse hooks share the same t=0.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SessionManager, cls).__new__(cls)
                cls._instance.is_recording = False
                cls._instance.start_time = 0.0
        return cls._instance

    def start_session(self):
        """Initializes the baseline clock."""
        self.is_recording = True
        self.start_time = time.perf_counter()

    def stop_session(self):
        self.is_recording = False

    def get_timestamp(self) -> float:
        """Returns elapsed time in seconds since recording started."""
        if not self.is_recording:
            return 0.0
        return time.perf_counter() - self.start_time