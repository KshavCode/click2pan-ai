import math

class EventProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.debounce_thresh = config["animation_settings"]["debounce_threshold_ms"] / 1000.0
        self.screen_w = float(config["video_settings"]["resolution"]["width"])
        self.screen_h = float(config["video_settings"]["resolution"]["height"])
        self.zoom_factor = config["video_settings"]["zoom_factor"]
        
        self.zoom_w = self.screen_w / self.zoom_factor
        self.zoom_h = self.screen_h / self.zoom_factor
        
        # Space threshold: if clicks are within this many pixels, they are grouped
        self.space_threshold = 200.0

    def process_raw_events(self, raw_events: list[dict]) -> list[dict]:
        """Filters rapid clicks and outputs clean target boxes and raw click ripples."""
        if not raw_events:
            return []

        # 0. Filter out multi-monitor out-of-bounds clicks
        valid_events = [e for e in raw_events if 0.0 <= e["x"] <= self.screen_w and 0.0 <= e["y"] <= self.screen_h]
        if not valid_events:
            return []

        # 1. Cluster rapid LEFT clicks that are close together spatially
        left_events = [e for e in valid_events if e["button"] == "left"]
        clustered = self._cluster_events(left_events)
        
        processed = []

        for c in clustered:
            target_box = self._calculate_clamped_bounds(c["x"], c["y"])
            processed.append({
                "type": "zoom",
                "start_time": c["start_time"],
                "end_time": c["end_time"],
                "target_box": target_box
            })

        # 2. Pass all valid events (left and right) for drawing visual ripples
        for e in valid_events:
            processed.append({
                "type": "click",
                "timestamp": e["timestamp"],
                "click_x": e["x"],
                "click_y": e["y"],
                "button": e["button"]
            })

        return processed

    def _cluster_events(self, events: list[dict]) -> list[dict]:
        """
        Groups clicks occurring within the time threshold AND space threshold.
        Tracks both the start and end time of the cluster to ensure zooms don't drop out early.
        """
        if not events:
            return []
            
        clustered = []
        
        current_cluster = {
            "start_time": events[0]["timestamp"],
            "end_time": events[0]["timestamp"],
            "x": events[0]["x"],
            "y": events[0]["y"],
            "count": 1
        }

        for i in range(1, len(events)):
            evt = events[i]
            time_diff = evt["timestamp"] - current_cluster["end_time"]
            distance = math.hypot(evt["x"] - current_cluster["x"], evt["y"] - current_cluster["y"])

            if time_diff < self.debounce_thresh and distance < self.space_threshold:
                # Group them! Update the end_time to the latest click in the cluster
                current_cluster["end_time"] = evt["timestamp"]
                # Average the coordinates (centroid)
                total_x = (current_cluster["x"] * current_cluster["count"]) + evt["x"]
                total_y = (current_cluster["y"] * current_cluster["count"]) + evt["y"]
                current_cluster["count"] += 1
                current_cluster["x"] = total_x / current_cluster["count"]
                current_cluster["y"] = total_y / current_cluster["count"]
            else:
                # Finish current cluster and start a new one
                clustered.append(current_cluster)
                current_cluster = {
                    "start_time": evt["timestamp"],
                    "end_time": evt["timestamp"],
                    "x": evt["x"],
                    "y": evt["y"],
                    "count": 1
                }
                
        clustered.append(current_cluster)
        return clustered

    def _calculate_clamped_bounds(self, click_x: float, click_y: float) -> dict:
        """Calculates the top-left (x,y) of the zoom crop, clamping to screen edges."""
        target_x = click_x - (self.zoom_w / 2)
        target_y = click_y - (self.zoom_h / 2)

        target_x = max(0.0, min(self.screen_w - self.zoom_w, target_x))
        target_y = max(0.0, min(self.screen_h - self.zoom_h, target_y))

        return {
            "x": target_x,
            "y": target_y,
            "width": self.zoom_w,
            "height": self.zoom_h
        }