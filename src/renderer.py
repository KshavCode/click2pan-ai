import os
from moviepy import VideoFileClip
import cv2
import numpy as np

class Renderer:
    def __init__(self, config: dict):
        self.config = config
        self.hold_duration = config["animation_settings"]["hold_duration_ms"] / 1000.0
        self.trans_duration = config["animation_settings"]["zoom_duration_ms"] / 1000.0
        self.screen_w = float(config["video_settings"]["resolution"]["width"])
        self.screen_h = float(config["video_settings"]["resolution"]["height"])
        self.screen_box = {"x": 0.0, "y": 0.0, "width": self.screen_w, "height": self.screen_h}

    def _interpolate(self, box1, box2, progress):
        progress = max(0.0, min(1.0, progress))
        # ease-in-out curve
        progress = progress * progress * (3 - 2 * progress)
        
        return {
            "x": box1["x"] + (box2["x"] - box1["x"]) * progress,
            "y": box1["y"] + (box2["y"] - box1["y"]) * progress,
            "width": box1["width"] + (box2["width"] - box1["width"]) * progress,
            "height": box1["height"] + (box2["height"] - box1["height"]) * progress
        }

    def _build_timeline(self, events):
        """Constructs a flat timeline of keyframes to guarantee smooth interpolation."""
        keyframes = [(0.0, self.screen_box)]
        
        # Only build timeline from zoom events
        zoom_events = [e for e in events if e.get("type") == "zoom"]
        
        for ev in zoom_events:
            t_start = ev["start_time"]
            t_end = ev["end_time"]
            box = ev["target_box"]
            
            # 1. Start zoom-in transition
            t_start_trans = t_start - self.trans_duration
            
            if keyframes and t_start_trans > keyframes[-1][0]:
                keyframes.append((t_start_trans, self.screen_box))
                
            # 2. Overwrite any keyframes that happen after t_start
            keyframes = [kf for kf in keyframes if kf[0] < t_start]
            
            # 3. Add the new hold spanning the entire cluster duration
            keyframes.append((t_start, box))
            keyframes.append((t_end + self.hold_duration, box))
            
        if keyframes:
            last_t = keyframes[-1][0]
            keyframes.append((last_t + self.trans_duration, self.screen_box))
            keyframes.append((last_t + self.trans_duration + 99999.0, self.screen_box))
            
        return keyframes

    def get_box_at_time(self, t, keyframes):
        for i in range(len(keyframes) - 1):
            t1, box1 = keyframes[i]
            t2, box2 = keyframes[i+1]
            if t1 <= t <= t2:
                if t1 == t2:
                    return box1
                progress = (t - t1) / (t2 - t1)
                return self._interpolate(box1, box2, progress)
        
        return self.screen_box

    def render(self, input_video: str, events: list[dict], output_video: str, progress_callback=None):
        if not os.path.exists(input_video):
            raise FileNotFoundError(f"Input video not found: {input_video}")
            
        os.makedirs(os.path.dirname(os.path.abspath(output_video)), exist_ok=True)

        print("Loading video into MoviePy...")
        clip = VideoFileClip(input_video)
        
        if not events:
            print("No events found. Exporting exact copy.")
            clip.write_videofile(output_video, codec="libx264", audio_codec="aac")
            return

        keyframes = self._build_timeline(events)
        click_events = [e for e in events if e.get("type") == "click"]

        def transform_frame(get_frame, t):
            frame = get_frame(t)
            
            # 1. Apply visual click indicators (ripple effect)
            for ev in click_events:
                t_click = ev["timestamp"]
                if t_click <= t <= t_click + 0.4:
                    progress = (t - t_click) / 0.4
                    radius = int(10 + 50 * progress)
                    alpha = 1.0 - progress
                    overlay = frame.copy()
                    
                    click_x = int(round(ev["click_x"]))
                    click_y = int(round(ev["click_y"]))
                    
                    # Yellow for left, Red for right
                    color = (0, 255, 255) if ev.get("button", "left") == "left" else (0, 0, 255)
                    cv2.circle(overlay, (click_x, click_y), radius, color, 4)
                    frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

            # 2. Compute smooth pan/zoom
            box = self.get_box_at_time(t, keyframes)
            
            x = int(round(box["x"]))
            y = int(round(box["y"]))
            w = int(round(box["width"]))
            h = int(round(box["height"]))
            
            x = max(0, min(frame.shape[1] - 1, x))
            y = max(0, min(frame.shape[0] - 1, y))
            w = max(1, min(frame.shape[1] - x, w))
            h = max(1, min(frame.shape[0] - y, h))
            
            cropped = frame[y:y+h, x:x+w]
            
            # 3. High quality text resize
            resized = cv2.resize(cropped, (int(self.screen_w), int(self.screen_h)), interpolation=cv2.INTER_LANCZOS4)
            return resized

        print("Applying dynamic smooth zoom transitions...")
        processed_clip = clip.transform(transform_frame)
        
        # Setup custom logger for progress bar
        from proglog import ProgressBarLogger
        class MyBarLogger(ProgressBarLogger):
            def bars_callback(self, bar, attr, value, old_value=None):
                if bar == 't' and progress_callback:
                    total = self.bars[bar]['total']
                    if total > 0:
                        progress_callback(value / total)

        logger = MyBarLogger() if progress_callback else 'bar'
        
        print(f"Exporting final video to {output_video}...")
        processed_clip.write_videofile(
            output_video, 
            codec="libx264", 
            audio_codec="aac",
            preset="fast",
            threads=4,
            logger=logger
        )
        print("Render complete!")
