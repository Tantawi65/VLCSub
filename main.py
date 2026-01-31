"""
VLC Subtitle Learner - Main Application
Learn languages while watching movies with clickable subtitle overlay
"""

from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import os
import sys

from srt_parser import parse_srt_file, Subtitle
from sync_engine import SubtitleSync
from vocabulary_saver import VocabularySaver
from subtitle_overlay import SubtitleOverlay, ControlPanel


class VLCSubtitleLearner:
    """
    Main application class that integrates all components
    """
    
    # Default configuration
    DEFAULT_CONFIG = {
        'font_size': 28,
        'bg_color': '#1a1a1a',      # Dark gray - visible but subtle
        'fg_color': '#ffffff',
        'opacity': 0.92,            # Slightly more opaque for easier clicking
        'sync_step_ms': 500,        # How much +/- adjusts
        'update_interval_ms': 40,   # How often to check for new subtitle
        'vocabulary_file': 'vocabulary.json'
    }
    
    def __init__(self):
        # Main Tk root (hidden)
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Configuration
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Components
        self.sync: SubtitleSync = None
        self.vocab = VocabularySaver(self.config['vocabulary_file'])
        self.current_srt_file = ""
        self.current_subtitle: Subtitle = None
        self.saved_words_set: set = set(self.vocab.get_unique_words())
        self.sync_mode = 'manual'
        self.vlc_last_ok = True
        
        # Create UI components
        self._create_ui()
        
        # Bind global keyboard shortcuts
        self._bind_shortcuts()
        
        # Start update loop
        self._update_loop()
    
    def _create_ui(self):
        """Create the UI windows"""
        # Create subtitle overlay (VLC-style, starts hidden)
        self.overlay = SubtitleOverlay(
            self.root,
            on_word_click=self._on_word_click,
            font_size=self.config['font_size'],
            bg_color=self.config['bg_color'],
            fg_color=self.config['fg_color'],
            opacity=self.config['opacity']
        )
        
        # Create control panel with settings callback
        self.control_panel = ControlPanel(
            self.root,
            on_load_srt=self._load_srt_file,
            on_start=self._start_playback,
            on_pause=self._pause_playback,
            on_reset=self._reset_playback,
            on_export=self._export_vocabulary,
            on_settings_change=self._on_settings_change,
            vocabulary_saver=self.vocab
        )
        
        # Position control panel at top-right
        screen_width = self.root.winfo_screenwidth()
        self.control_panel.geometry(f"+{screen_width - 450}+50")
        
        # Update initial stats
        self._update_stats()
    
    def _on_settings_change(self, settings: dict):
        """Handle settings changes from control panel"""
        # Handle sync offset adjustment from button
        if 'sync_adjust' in settings:
            self._adjust_sync(settings['sync_adjust'])
            # Always update the permanent label
            if hasattr(self, 'control_panel') and self.sync is not None:
                self.control_panel.set_sync_offset(self.sync.offset_ms)
            # Show status if requested (only when sync_adjust is present)
            if (settings.get('show_offset_status') or True) and hasattr(self, 'control_panel') and self.sync is not None:
                self.control_panel.show_sync_offset_status(self.sync.offset_ms)
            return
        self.overlay.apply_settings(settings)
        # Update config
        self.config['font_size'] = settings.get('font_size', self.config['font_size'])
        self.config['opacity'] = settings.get('opacity', self.config['opacity'])
        self.config['bg_color'] = settings.get('bg_color', self.config['bg_color'])
        self.sync_mode = settings.get('sync_mode', 'manual')
        # Always update the permanent label after any settings change
        if hasattr(self, 'control_panel') and self.sync is not None:
            self.control_panel.set_sync_offset(self.sync.offset_ms)
    
    def _bind_shortcuts(self):
        """Bind keyboard shortcuts to control panel"""
        # Bind to control panel (since overlay is borderless and may not receive focus)
        self.control_panel.bind('<space>', lambda e: self._toggle_playback())
        self.control_panel.bind('<plus>', lambda e: self._adjust_sync(-self.config['sync_step_ms']))
        self.control_panel.bind('<minus>', lambda e: self._adjust_sync(self.config['sync_step_ms']))
        self.control_panel.bind('<equal>', lambda e: self._adjust_sync(-self.config['sync_step_ms']))
        self.control_panel.bind('<KP_Add>', lambda e: self._adjust_sync(-self.config['sync_step_ms']))
        self.control_panel.bind('<KP_Subtract>', lambda e: self._adjust_sync(self.config['sync_step_ms']))
        self.control_panel.bind('<Escape>', lambda e: self._toggle_overlay())
        self.control_panel.bind('<f>', lambda e: self._cycle_font_size())
        self.control_panel.bind('<F>', lambda e: self._cycle_font_size())
        self.control_panel.bind('<r>', lambda e: self._reset_playback())
        self.control_panel.bind('<R>', lambda e: self._reset_playback())
        self.control_panel.bind('<Right>', lambda e: self._adjust_sync(-100))
        self.control_panel.bind('<Left>', lambda e: self._adjust_sync(100))
        self.control_panel.bind('<g>', lambda e: self._sync_offset_back())
        self.control_panel.bind('<h>', lambda e: self._sync_offset_forward())
        
        # Focus control panel for keyboard input
        self.control_panel.focus_set()
    
    def _load_srt_file(self, filepath: str):
        """Load and parse an SRT file"""
        try:
            subtitles = parse_srt_file(filepath)
            
            if not subtitles:
                messagebox.showerror("Error", "No subtitles found in file")
                return
            
            self.sync = SubtitleSync(subtitles)
            self.current_srt_file = os.path.basename(filepath)
            
            # Update control panel
            self.control_panel.update_file_info(
                self.current_srt_file,
                len(subtitles)
            )
            
            # Show ready message (subtitle will appear when started)
            print(f"Loaded {len(subtitles)} subtitles from {filepath}")
            print("Press Space or click Start when the movie begins!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load SRT file:\n{str(e)}")
    
    def _start_playback(self):
        """Start subtitle playback"""
        if self.sync is None:
            messagebox.showwarning("Warning", "Please load an SRT file first")
            return
        
        self.sync.start()
        self.overlay.focus_set()
        print("Playback started")
    
    def _pause_playback(self):
        """Pause subtitle playback"""
        if self.sync:
            self.sync.pause()
            print("Playback paused")
    
    def _toggle_playback(self):
        """Toggle play/pause"""
        if self.sync is None:
            return
        
        self.sync.toggle()
        status = "playing" if self.sync.is_running else "paused"
        print(f"Playback {status}")
    
    def _reset_playback(self):
        """Reset playback to beginning"""
        if self.sync:
            self.sync.reset()
            self.overlay.clear_subtitle()
            print("Playback reset")
    
    def _adjust_sync(self, delta_ms: int):
        """
        Adjust subtitle timing
        
        User perspective:
        - Press + when subtitles are LATE → we need to show them EARLIER (negative delta to internal offset)
        - Press - when subtitles are EARLY → we need to show them LATER (positive delta to internal offset)
        
        The delta passed here is already inverted in the key bindings above
        """
        if self.sync:
            self.sync.adjust_offset(delta_ms)
            print(f"Sync adjusted to {self.sync.offset_ms:+d}ms")
            if hasattr(self, 'control_panel'):
                self.control_panel.set_sync_offset(self.sync.offset_ms)
                self.control_panel.show_sync_offset_status(self.sync.offset_ms)
    
    def _sync_offset_back(self):
        """Move subtitles back (earlier) by 100ms"""
        if self.sync:
            self.sync.adjust_offset(-100)
            print(f"Sync offset: {self.sync.offset_ms:+d}ms")
            if hasattr(self, 'control_panel'):
                self.control_panel.set_sync_offset(self.sync.offset_ms)
                self.control_panel.show_sync_offset_status(self.sync.offset_ms)

    def _sync_offset_forward(self):
        """Move subtitles forward (later) by 100ms"""
        if self.sync:
            self.sync.adjust_offset(100)
            print(f"Sync offset: {self.sync.offset_ms:+d}ms")
            if hasattr(self, 'control_panel'):
                self.control_panel.set_sync_offset(self.sync.offset_ms)
                self.control_panel.show_sync_offset_status(self.sync.offset_ms)

    def _toggle_overlay(self):
        """Show/hide the subtitle overlay"""
        if self.overlay.winfo_viewable():
            self.overlay.hide()
        else:
            self.overlay.show()
    
    def _cycle_font_size(self):
        """Cycle through font sizes"""
        sizes = [22, 26, 30, 36, 42]
        current = self.config['font_size']
        
        # Find next size
        try:
            idx = sizes.index(current)
            next_idx = (idx + 1) % len(sizes)
        except ValueError:
            next_idx = 0
        
        self.config['font_size'] = sizes[next_idx]
        self.overlay.set_font_size(sizes[next_idx])
        print(f"Font size: {sizes[next_idx]}")
    
    def _on_word_click(self, word: str, sentence: str, timestamp_ms: int):
        """Handle when user clicks a word"""
        # Save to vocabulary
        entry = self.vocab.add_word(
            word=word,
            sentence=sentence,
            timestamp_ms=timestamp_ms,
            movie_file=self.current_srt_file
        )
        
        # Update saved words set
        self.saved_words_set.add(word.lower())
        
        # Visual feedback
        self.overlay.flash_saved()
        
        # Update stats
        self._update_stats()
        
        print(f"Saved: '{word}' @ {entry.timestamp_formatted}")
    
    def _update_stats(self):
        """Update the statistics display"""
        stats = self.vocab.get_stats()
        self.control_panel.update_stats(
            stats['total_saves'],
            stats['unique_words']
        )
    
    def _export_vocabulary(self):
        """Export vocabulary to CSV"""
        try:
            csv_path = self.vocab.export_to_csv()
            messagebox.showinfo(
                "Export Complete",
                f"Vocabulary exported to:\n{csv_path}\n\nYou can import this into Anki!"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export:\n{str(e)}")
    
    def _update_loop(self):
        """Main update loop - checks for subtitle changes or VLC time"""
        import requests
        import json
        vlc_url = 'http://localhost:8080/requests/status.json'
        vlc_auth = ('', 'vlc123')
        use_vlc = self.sync_mode == 'vlc'
        vlc_ok = False
        vlc_time = None
        if use_vlc:
            try:
                r = requests.get(vlc_url, timeout=0.05, auth=vlc_auth)
                if r.status_code == 200:
                    data = r.json()
                    vlc_time = int(float(data.get('time', 0)) * 1000)
                    vlc_ok = True
            except Exception:
                vlc_ok = False
        if use_vlc and vlc_ok and self.sync:
            self.vlc_last_ok = True
            self.sync.set_playback_time(vlc_time)
            current = self.sync.get_current_subtitle()
            if current != self.current_subtitle:
                self.current_subtitle = current
                if current:
                    self.overlay.update_subtitle(current.text, current.start_ms, self.saved_words_set)
                else:
                    self.overlay.clear_subtitle()
        else:
            if use_vlc and not vlc_ok:
                if self.vlc_last_ok:
                    print("VLC not reachable, falling back to manual mode.")
                self.vlc_last_ok = False
            # Manual mode fallback
            if self.sync and self.sync.is_running:
                current = self.sync.get_current_subtitle()
                if current != self.current_subtitle:
                    self.current_subtitle = current
                    if current:
                        self.overlay.update_subtitle(current.text, current.start_ms, self.saved_words_set)
                    else:
                        self.overlay.clear_subtitle()
        # Update status bar
        if self.sync:
            info = self.sync.get_progress_info()
            self.overlay.update_status(info['is_running'], info['elapsed'], info['offset_str'])
        self.root.after(self.config['update_interval_ms'], self._update_loop)
    
    def run(self):
        """Start the application"""
        print("=" * 50)
        print("VLC Subtitle Learner")
        print("=" * 50)
        print("\nInstructions:")
        print("1. Load an SRT file using the control panel")
        print("2. Start your movie in VLC (with subtitles OFF)")
        print("3. Press Start or Space when the movie begins")
        print("4. Click any word you want to save")
        print("\nKeyboard shortcuts:")
        print("  Space     - Play/Pause")
        print("  +/=       - Subtitles late? Move forward")
        print("  -         - Subtitles early? Move backward")
        print("  ←/→       - Fine-tune sync (100ms)")
        print("  F         - Cycle font size")
        print("  R         - Reset to beginning")
        print("  Esc       - Hide/show overlay")
        print("  G         - Sync offset back (100ms)")
        print("  H         - Sync offset forward (100ms)")
        print("=" * 50)
        
        self.root.mainloop()


def main():
    """Entry point"""
    app = VLCSubtitleLearner()
    app.run()


if __name__ == "__main__":
    main()
