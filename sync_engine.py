"""
Subtitle Sync Engine
Handles timing, playback state, and offset adjustments
"""

from __future__ import annotations
import time
from typing import Callable, List, Optional
from srt_parser import Subtitle, get_subtitle_at_time


class SubtitleSync:
    """
    Manages subtitle timing and synchronization
    
    The sync engine tracks:
    - When playback started (real wall clock time)
    - Current offset adjustment (user can add/subtract time)
    - Playback state (running/paused)
    """
    def __init__(self, subtitles: List[Subtitle]):
        self.subtitles = subtitles
        self._start_time = None  # Wall clock when started
        self._offset_ms = 0      # User adjustment offset
        self._is_running = False
        self._pause_elapsed = 0  # Time elapsed when paused
        self._current_subtitle = None

    def set_playback_time(self, time_ms: int):
        """Set the playback time directly (used for VLC sync mode)"""
        self._pause_elapsed = time_ms
        if self._is_running:
            self._start_time = time.time() - (time_ms / 1000.0)
        
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def offset_ms(self) -> int:
        return self._offset_ms
    
    @property
    def offset_seconds(self) -> float:
        return self._offset_ms / 1000.0
    
    def start(self):
        """Start or resume subtitle playback"""
        if self._is_running:
            return
        
        if self._start_time is None:
            # Fresh start
            self._start_time = time.time()
            self._pause_elapsed = 0
        else:
            # Resume from pause - adjust start time to account for pause duration
            self._start_time = time.time() - (self._pause_elapsed / 1000.0)
        
        self._is_running = True
    
    def pause(self):
        """Pause subtitle playback"""
        if not self._is_running:
            return
        
        self._pause_elapsed = self.get_elapsed_ms()
        self._is_running = False
    
    def toggle(self):
        """Toggle between play and pause"""
        if self._is_running:
            self.pause()
        else:
            self.start()
    
    def reset(self):
        """Reset playback to beginning"""
        self._start_time = None
        self._pause_elapsed = 0
        self._is_running = False
        self._current_subtitle = None
    
    def adjust_offset(self, delta_ms: int):
        """
        Adjust the sync offset
        
        Positive delta: subtitles appear LATER (use when subs are early)
        Negative delta: subtitles appear EARLIER (use when subs are late)
        
        From user perspective:
        - Press '+' when subtitles are LATE (behind audio) → move forward (negative delta internally)
        - Press '-' when subtitles are EARLY (ahead of audio) → move backward (positive delta internally)
        """
        self._offset_ms += delta_ms
    
    def set_offset(self, offset_ms: int):
        """Set absolute offset value"""
        self._offset_ms = offset_ms
    
    def get_elapsed_ms(self) -> int:
        """Get current playback position in milliseconds"""
        if self._start_time is None:
            return 0
        
        if not self._is_running:
            return self._pause_elapsed
        
        # Calculate elapsed time since start
        elapsed_seconds = time.time() - self._start_time
        elapsed_ms = int(elapsed_seconds * 1000)
        
        return elapsed_ms
    
    def get_adjusted_time_ms(self) -> int:
        """Get current time adjusted by user offset"""
        return self.get_elapsed_ms() + self._offset_ms
    
    def get_current_subtitle(self) -> Optional[Subtitle]:
        """Get the subtitle that should be displayed now"""
        if not self.subtitles:
            return None
        
        current_time = self.get_adjusted_time_ms()
        return get_subtitle_at_time(self.subtitles, current_time)
    
    def seek_to(self, time_ms: int):
        """Jump to a specific time"""
        self._pause_elapsed = time_ms
        if self._is_running:
            self._start_time = time.time() - (time_ms / 1000.0)
    
    def get_progress_info(self) -> dict:
        """Get current playback info for display"""
        elapsed = self.get_elapsed_ms()
        adjusted = self.get_adjusted_time_ms()
        
        # Format as MM:SS
        def format_time(ms):
            total_seconds = max(0, ms // 1000)
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        
        # Get total duration from subtitles
        total_ms = 0
        if self.subtitles:
            total_ms = self.subtitles[-1].end_ms
        
        return {
            "elapsed": format_time(elapsed),
            "elapsed_ms": elapsed,
            "adjusted_ms": adjusted,
            "total": format_time(total_ms),
            "total_ms": total_ms,
            "offset": self._offset_ms,
            "offset_str": f"{self._offset_ms:+d}ms",
            "is_running": self._is_running
        }
    
    def get_nearby_subtitles(self, count: int = 3) -> List[Subtitle]:
        """Get subtitles around current time for preview"""
        if not self.subtitles:
            return []
        
        current_time = self.get_adjusted_time_ms()
        
        # Find closest subtitle index
        closest_idx = 0
        min_diff = float('inf')
        
        for i, sub in enumerate(self.subtitles):
            diff = abs(sub.start_ms - current_time)
            if diff < min_diff:
                min_diff = diff
                closest_idx = i
        
        # Return surrounding subtitles
        start_idx = max(0, closest_idx - count // 2)
        end_idx = min(len(self.subtitles), start_idx + count)
        
        return self.subtitles[start_idx:end_idx]


# Testing
if __name__ == "__main__":
    from srt_parser import Subtitle
    
    # Create test subtitles
    test_subs = [
        Subtitle(1, 1000, 4000, "First subtitle"),
        Subtitle(2, 5000, 8000, "Second subtitle"),
        Subtitle(3, 10000, 13000, "Third subtitle"),
    ]
    
    sync = SubtitleSync(test_subs)
    
    print("Starting sync test...")
    sync.start()
    
    for i in range(15):
        time.sleep(0.5)
        info = sync.get_progress_info()
        current = sync.get_current_subtitle()
        
        sub_text = current.text if current else "(no subtitle)"
        print(f"Time: {info['elapsed']} | Offset: {info['offset_str']} | Sub: {sub_text}")
        
        # Test offset adjustment at 3 seconds
        if i == 6:
            print("  → Adjusting offset by +2000ms")
            sync.adjust_offset(2000)
