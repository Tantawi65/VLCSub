"""
Floating Subtitle Window
Minimal overlay UI with clickable words
"""

import tkinter as tk
from tkinter import font as tkfont
import re
import os
import webbrowser
import csv              # Added for CSV export
import datetime         # Added for timestamping filenames
from typing import Callable, Optional, List

class ClickableWord(tk.Label):
    """A label that acts as a clickable word - styled like real subtitles"""
    
    def __init__(
        self,
        parent,
        word: str,
        on_click: Callable[[str], None],
        on_drag_start: Callable,
        on_drag_motion: Callable,
        on_drag_end: Callable,
        font_config: dict,
        bg_color: str = '#1a1a1a',
        **kwargs
    ):
        self.word = word
        self.on_click = on_click
        self.on_drag_start = on_drag_start
        self.on_drag_motion = on_drag_motion
        self.on_drag_end = on_drag_end
        self.is_saved = False
        self._click_start_pos = None
        self.bg_color = bg_color
        
        # VLC-style subtitle colors
        self.normal_fg = kwargs.pop('fg', '#ffffff')
        self.hover_fg = '#ffff00'  # Yellow on hover like VLC
        self.saved_fg = '#00ff00'  # Green for saved
        
        super().__init__(
            parent,
            text=word,
            font=(font_config.get('family', 'Arial'), 
                  font_config.get('size', 28),
                  'bold'),
            bg=bg_color,
            fg=self.normal_fg,
            cursor="hand2",
            padx=4,   # Larger horizontal padding for easier clicking
            pady=8,   # Larger vertical padding for easier clicking
            **kwargs
        )
        
        # Bind events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<B1-Motion>", self._on_motion)
    
    def _on_enter(self, event):
        """Mouse hover enter - yellow highlight"""
        if not self.is_saved:
            self.config(fg=self.hover_fg)
    
    def _on_leave(self, event):
        """Mouse hover leave"""
        if self.is_saved:
            self.config(fg=self.saved_fg)
        else:
            self.config(fg=self.normal_fg)
    
    def _on_press(self, event):
        """Mouse button pressed - record position for drag detection"""
        self._click_start_pos = (event.x_root, event.y_root)
        self.on_drag_start(event)
    
    def _on_release(self, event):
        """Mouse button released - click if not dragged"""
        if self._click_start_pos:
            dx = abs(event.x_root - self._click_start_pos[0])
            dy = abs(event.y_root - self._click_start_pos[1])
            # Only count as click if mouse didn't move much (not a drag)
            if dx < 5 and dy < 5:
                self.is_saved = True
                self.config(fg=self.saved_fg)
                self.on_click(self.word)
        self._click_start_pos = None
        self.on_drag_end(event)
    
    def _on_motion(self, event):
        """Mouse dragging"""
        self.on_drag_motion(event)
    
    def mark_as_saved(self):
        """Mark this word as already saved"""
        self.is_saved = True
        self.config(fg=self.saved_fg)


class SubtitleOverlay(tk.Toplevel):
    """
    Clean floating subtitle display - VLC style
    
    Features:
    - No window frame, just text with dark background
    - Semi-transparent dark background for easy clicking
    - White text, yellow hover, green saved
    - Draggable anywhere
    - Centered on screen
    """
    
    def __init__(
        self,
        parent,
        on_word_click: Callable[[str, str, int], None],
        font_size: int = 28,
        bg_color: str = '#1a1a1a',  # Dark gray, not pure black
        fg_color: str = '#ffffff',
        opacity: float = 0.88,
        width: int = 800,
        height: int = 80
    ):
        super().__init__(parent)
        
        self.on_word_click = on_word_click
        self.font_size = font_size
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.current_text = ""
        self.current_timestamp = 0
        self.word_labels = []
        self.saved_words_cache = set()
        
        # Window setup - borderless
        self.title("")
        self.configure(bg=bg_color)
        
        # Remove window decorations completely
        self.overrideredirect(True)
        
        # Always on top
        self.attributes('-topmost', True)
        
        # Semi-transparent (NOT fully transparent - allows clicking on background)
        self.attributes('-alpha', opacity)
        
        # NO transparentcolor - we want the dark background to be clickable!
        # This makes it much easier to click on words
        
        # Dragging state
        self._drag_data = {"x": 0, "y": 0, "dragging": False}
        self._vertical_only = True  # Default: center horizontally, drag vertically only
        
        # Store current window position
        self._current_x = 0
        self._current_y = 0
        
        # Create minimal UI
        self._create_ui()
        
        # Position at bottom center
        self._position_at_bottom()
        
        # Initially hidden until subtitles start
        self.withdraw()
    
    def _create_ui(self):
        """Create clean subtitle display - centered"""
        # Container frame with centered content
        self.word_container = tk.Frame(self, bg=self.bg_color)
        self.word_container.pack(expand=True, pady=5, padx=15)
        
        # Bind drag events to window background
        self.bind("<ButtonPress-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag_motion)
        self.bind("<ButtonRelease-1>", self._on_drag_end)
        self.word_container.bind("<ButtonPress-1>", self._on_drag_start)
        self.word_container.bind("<B1-Motion>", self._on_drag_motion)
        self.word_container.bind("<ButtonRelease-1>", self._on_drag_end)
    
    def _position_at_bottom(self):
        """Position overlay at bottom center of screen"""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Center horizontally, near bottom
        self._current_x = (screen_width // 2) - 400
        self._current_y = screen_height - 180
        
        self.geometry(f"+{self._current_x}+{self._current_y}")
    
    def _on_drag_start(self, event):
        """Start dragging"""
        self._drag_data["x"] = event.x_root
        self._drag_data["y"] = event.y_root
        self._drag_data["dragging"] = True
    
    def _on_drag_end(self, event):
        """End dragging"""
        self._drag_data["dragging"] = False
    
    def _on_drag_motion(self, event):
        """Handle dragging - move window vertically only or freely"""
        if not self._drag_data.get("dragging", False):
            return
        
        deltax = event.x_root - self._drag_data["x"]
        deltay = event.y_root - self._drag_data["y"]
        
        if self._vertical_only:
            # Keep centered horizontally, only move vertically
            self._current_y += deltay
            screen_width = self.winfo_screenwidth()
            self.update_idletasks()
            window_width = self.winfo_width()
            if window_width < 10:
                window_width = self.winfo_reqwidth()
            self._current_x = (screen_width - window_width) // 2
        else:
            # Free drag in all directions
            self._current_x += deltax
            self._current_y += deltay
            self._drag_data["x"] = event.x_root
        
        self._drag_data["y"] = event.y_root
        self.geometry(f"+{self._current_x}+{self._current_y}")
    
    def _center_horizontally_at_y(self, y: int = None):
        """Position window centered horizontally at given Y position"""
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        window_width = self.winfo_width()
        if window_width < 10:
            window_width = self.winfo_reqwidth()
        
        if y is None:
            y = self._current_y
        self._current_x = (screen_width - window_width) // 2
        self._current_y = y
        self.geometry(f"+{self._current_x}+{self._current_y}")
    
    def set_drag_mode(self, vertical_only: bool):
        """Set drag mode - vertical only (centered) or free drag"""
        self._vertical_only = vertical_only
        if vertical_only:
            # Re-center horizontally at current Y position
            self._center_horizontally_at_y(self._current_y)
    
    def update_subtitle(self, text: str, timestamp_ms: int, saved_words: set = None):
        """Update displayed subtitle with clickable words - centered"""
        if saved_words is None:
            saved_words = set()
        
        self.saved_words_cache = saved_words
        self.current_text = text
        self.current_timestamp = timestamp_ms
        
        # Clear existing
        for label in self.word_labels:
            label.destroy()
        self.word_labels.clear()
        
        if not text:
            self.withdraw()  # Hide when no subtitle
            return
        
        # Show window
        self.deiconify()
        
        # Split into words and punctuation
        tokens = re.findall(r"[\w']+|[.,!?;:\-\"'()…»«]|\s+", text)
        
        font_config = {'family': 'Arial', 'size': self.font_size}
        
        for token in tokens:
            if token.isspace():
                # Minimal space between words (words have their own padding)
                continue  # Skip spaces - word padding handles spacing
                
            elif re.match(r'^[\w\']+$', token):
                # Clickable word with good padding
                word_label = ClickableWord(
                    self.word_container,
                    word=token,
                    on_click=lambda w: self._handle_word_click(w),
                    on_drag_start=self._on_drag_start,
                    on_drag_motion=self._on_drag_motion,
                    on_drag_end=self._on_drag_end,
                    font_config=font_config,
                    bg_color=self.bg_color,
                    fg=self.fg_color
                )
                
                if token.lower() in saved_words:
                    word_label.mark_as_saved()
                
                word_label.pack(side=tk.LEFT)
                self.word_labels.append(word_label)
            else:
                # Punctuation - attached to previous word
                punct = tk.Label(
                    self.word_container,
                    text=token,
                    font=('Arial', self.font_size, 'bold'),
                    bg=self.bg_color,
                    fg='#aaaaaa',
                    padx=0,
                    pady=8
                )
                punct.pack(side=tk.LEFT)
                punct.bind("<ButtonPress-1>", lambda e: self._on_drag_start(e))
                punct.bind("<B1-Motion>", lambda e: self._on_drag_motion(e))
                punct.bind("<ButtonRelease-1>", lambda e: self._on_drag_end(e))
                self.word_labels.append(punct)
        
        # Resize and re-center window to fit content (only if vertical-only mode)
        self.update_idletasks()
        if self._vertical_only:
            self._center_horizontally_at_y(self._current_y)
    
    def _handle_word_click(self, word: str):
        """Handle word click"""
        self.on_word_click(word, self.current_text, self.current_timestamp)
    
    def update_status(self, is_running: bool, time_str: str, offset_str: str):
        """Status updates (no visible status bar in clean mode)"""
        pass  # No status bar in VLC-style mode
    
    def clear_subtitle(self):
        """Clear and hide"""
        for label in self.word_labels:
            label.destroy()
        self.word_labels.clear()
        self.current_text = ""
        self.withdraw()
    
    def set_font_size(self, size: int):
        """Update font size"""
        self.font_size = size
        if self.current_text:
            self.update_subtitle(self.current_text, self.current_timestamp, self.saved_words_cache)
    
    def flash_saved(self):
        """Brief flash feedback when word saved"""
        pass  # Word turns green, no need for flash
    
    def show(self):
        """Show the overlay"""
        self.deiconify()
        self.lift()
    
    def hide(self):
        """Hide the overlay"""
        self.withdraw()
    
    def apply_settings(self, settings: dict):
        """Apply appearance settings from control panel"""
        transparent = settings.get('transparent', False)
        bg_color = settings.get('bg_color', '#1a1a1a')
        font_size = settings.get('font_size', 28)
        opacity = settings.get('opacity', 0.92)
        vertical_only = settings.get('vertical_only', True)
        
        # Update drag mode
        self.set_drag_mode(vertical_only)
        
        # Update font size
        self.font_size = font_size
        
        # Update opacity
        self.attributes('-alpha', opacity)
        
        # Handle transparent vs colored background
        if transparent:
            # Use a specific color for transparency
            self.bg_color = 'magenta'  # Use magenta as transparent key
            self.configure(bg='magenta')
            self.word_container.configure(bg='magenta')
            self.wm_attributes('-transparentcolor', 'magenta')
        else:
            # Remove transparent color and use solid background
            self.bg_color = bg_color
            self.configure(bg=bg_color)
            self.word_container.configure(bg=bg_color)
            # Clear transparent color (set to empty/invalid to disable)
            try:
                self.wm_attributes('-transparentcolor', '')
            except:
                pass  # Some systems may not support clearing this
        
        # Refresh subtitle display with new settings
        if self.current_text:
            self.update_subtitle(self.current_text, self.current_timestamp, self.saved_words_cache)


class ControlPanel(tk.Toplevel):
    """Control window with settings for subtitle appearance"""

    def set_sync_offset(self, offset_ms):
        """Update the permanent sync offset label"""
        msg = f"Sync offset: {offset_ms:+d}ms"
        self._sync_offset_permanent_label.config(text=msg)
    
    def __init__(
        self,
        parent,
        on_load_srt: Callable[[str], None],
        on_start: Callable[[], None],
        on_pause: Callable[[], None],
        on_reset: Callable[[], None],
        on_export: Callable[[], None],
        on_settings_change: Callable[[dict], None] = None,
        vocabulary_saver = None
    ):
        super().__init__(parent)

        self.on_load_srt = on_load_srt
        self.on_start = on_start
        self.on_pause = on_pause
        self.on_reset = on_reset
        self.on_export = on_export
        self.on_settings_change = on_settings_change
        self.vocabulary_saver = vocabulary_saver
        self.vocab_viewer = None

        # Settings variables
        self.transparent_bg = tk.BooleanVar(value=False)
        self.bg_color = tk.StringVar(value='#1a1a1a')
        self.font_size = tk.IntVar(value=28)
        self.opacity = tk.DoubleVar(value=0.92)
        self.vertical_only = tk.BooleanVar(value=True)
        self.sync_mode = tk.StringVar(value='manual')

        self.title("VLC Subtitle Learner - Controls")
        self.configure(bg='#1a1a2e')
        self.resizable(True, True)
        self.minsize(400, 600)

        self._create_ui()

        # Ensure window fits all content and is visible
        self.update_idletasks()
        self.deiconify()
        self.lift()
        self.geometry("") 

        # For showing sync offset status
        self._sync_offset_status_label = None
        self._sync_offset_status_after_id = None
    
    def _create_ui(self):
        """Create control panel UI with settings"""
        # Main scrollable area
        main_frame = tk.Frame(self, bg='#1a1a2e')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Title
        title = tk.Label(
            main_frame,
            text="🎬 VLC Subtitle Learner",
            font=('Arial', 14, 'bold'),
            bg='#1a1a2e',
            fg='#ffffff'
        )
        title.pack(pady=(5, 5))

        # --- DEVELOPER CREDIT (Clickable) ---
        dev_label = tk.Label(
            main_frame,
            text="Developed by Mohamed Tantawi",
            font=('Arial', 10, 'underline'),
            fg='#4ecca3',
            bg='#1a1a2e',
            cursor="hand2"
        )
        dev_label.pack(pady=(0, 10))
        dev_label.bind("<Button-1>", lambda e: self._show_developer_info())

        # === FILE SECTION ===
        file_frame = tk.LabelFrame(main_frame, text="Subtitle File", bg='#1a1a2e', fg='#888888', font=('Arial', 9))
        file_frame.pack(fill=tk.X, pady=5)
        
        load_btn = tk.Button(
            file_frame,
            text="📂 Load SRT File",
            font=('Arial', 11),
            command=self._load_file,
            bg='#16213e',
            fg='#ffffff',
            activebackground='#0f3460',
            activeforeground='#ffffff',
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        load_btn.pack(pady=8)
        
        self.file_label = tk.Label(
            file_frame,
            text="No file loaded",
            font=('Arial', 9),
            bg='#1a1a2e',
            fg='#666666'
        )
        self.file_label.pack(pady=(0, 5))
        
        # === PLAYBACK SECTION ===
        playback_frame = tk.LabelFrame(main_frame, text="Playback", bg='#1a1a2e', fg='#888888', font=('Arial', 9))
        playback_frame.pack(fill=tk.X, pady=5)
        
        btn_container = tk.Frame(playback_frame, bg='#1a1a2e')
        btn_container.pack(pady=8)

        btn_style = {
            'font': ('Arial', 10),
            'bg': '#16213e',
            'fg': '#ffffff',
            'activebackground': '#0f3460',
            'activeforeground': '#ffffff',
            'relief': tk.FLAT,
            'padx': 12,
            'pady': 4
        }

        tk.Button(btn_container, text="▶ Start", command=self.on_start, **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_container, text="⏸ Pause", command=self.on_pause, **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_container, text="⏹ Reset", command=self.on_reset, **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btn_container, text="⏪ Back (G)",
            command=lambda: self._handle_sync_adjust(-100), **btn_style
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btn_container, text="⏩ Forward (H)",
            command=lambda: self._handle_sync_adjust(100), **btn_style
        ).pack(side=tk.LEFT, padx=3)

        # Permanent label for sync offset (always visible)
        self._sync_offset_permanent_label = tk.Label(
            playback_frame,
            text="Subtitle offset: 0 ms (no offset)",
            font=('Arial', 10, 'bold'),
            bg='#1a1a2e',
            fg='#4ecca3'
        )
        self._sync_offset_permanent_label.pack(pady=(0, 2))

        # Status label for sync offset (temporary popup, hidden by default)
        self._sync_offset_status_label = tk.Label(
            playback_frame,
            text="",
            font=('Arial', 10, 'bold'),
            bg='#1a1a2e',
            fg='#4ecca3'
        )
        self._sync_offset_status_label.pack_forget()

        # === SYNC MODE SECTION ===
        sync_frame = tk.LabelFrame(main_frame, text="Sync Mode", bg='#1a1a2e', fg='#888888', font=('Arial', 9))
        sync_frame.pack(fill=tk.X, pady=5)
        tk.Radiobutton(
            sync_frame,
            text="Manual (Default)",
            variable=self.sync_mode,
            value='manual',
            bg='#1a1a2e',
            fg='#ffffff',
            selectcolor='#0f3460',
            font=('Arial', 10),
            command=self._apply_settings
        ).pack(side=tk.LEFT, padx=10, pady=5)
        tk.Radiobutton(
            sync_frame,
            text="VLC (Auto)",
            variable=self.sync_mode,
            value='vlc',
            bg='#1a1a2e',
            fg='#ffffff',
            selectcolor='#0f3460',
            font=('Arial', 10),
            command=self._apply_settings
        ).pack(side=tk.LEFT, padx=10, pady=5)

        # === APPEARANCE SECTION ===
        appear_frame = tk.LabelFrame(main_frame, text="Appearance", bg='#1a1a2e', fg='#888888', font=('Arial', 9))
        appear_frame.pack(fill=tk.X, pady=5)

        # Transparent background checkbox
        trans_frame = tk.Frame(appear_frame, bg='#1a1a2e')
        trans_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Checkbutton(
            trans_frame,
            text="Transparent Background",
            variable=self.transparent_bg,
            command=self._apply_settings,
            bg='#1a1a2e',
            fg='#ffffff',
            selectcolor='#0f3460',
            activebackground='#1a1a2e',
            activeforeground='#ffffff',
            font=('Arial', 10)
        ).pack(side=tk.LEFT)

        # Background color picker
        color_frame = tk.Frame(appear_frame, bg='#1a1a2e')
        color_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(color_frame, text="Background Color:", bg='#1a1a2e', fg='#aaaaaa', font=('Arial', 10)).pack(side=tk.LEFT)

        self.color_preview = tk.Label(color_frame, text="   ", bg=self.bg_color.get(), width=3, relief=tk.SOLID)
        self.color_preview.pack(side=tk.LEFT, padx=5)

        tk.Button(
            color_frame,
            text="Choose",
            command=self._choose_color,
            bg='#16213e',
            fg='#ffffff',
            font=('Arial', 9),
            relief=tk.FLAT,
            padx=8
        ).pack(side=tk.LEFT, padx=5)

        # Preset colors
        presets_frame = tk.Frame(appear_frame, bg='#1a1a2e')
        presets_frame.pack(fill=tk.X, padx=10, pady=2)

        tk.Label(presets_frame, text="Presets:", bg='#1a1a2e', fg='#666666', font=('Arial', 9)).pack(side=tk.LEFT)

        preset_colors = [('#1a1a1a', 'Dark'), ('#000000', 'Black'), ('#0a0a2e', 'Navy'), ('#1a2e1a', 'Forest')]
        for color, name in preset_colors:
            btn = tk.Button(
                presets_frame,
                text="",
                bg=color,
                width=2,
                height=1,
                relief=tk.SOLID,
                command=lambda c=color: self._set_color(c)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # Font size slider
        font_frame = tk.Frame(appear_frame, bg='#1a1a2e')
        font_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(font_frame, text="Font Size:", bg='#1a1a2e', fg='#aaaaaa', font=('Arial', 10)).pack(side=tk.LEFT)

        self.font_label = tk.Label(font_frame, text="28", bg='#1a1a2e', fg='#4ecca3', font=('Arial', 10, 'bold'), width=3)
        self.font_label.pack(side=tk.RIGHT)

        font_slider = tk.Scale(
            font_frame,
            from_=18,
            to=48,
            orient=tk.HORIZONTAL,
            variable=self.font_size,
            command=lambda v: self._on_font_change(),
            bg='#1a1a2e',
            fg='#ffffff',
            troughcolor='#16213e',
            highlightthickness=0,
            length=150
        )
        font_slider.pack(side=tk.RIGHT, padx=5)

        # Opacity slider
        opacity_frame = tk.Frame(appear_frame, bg='#1a1a2e')
        opacity_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(opacity_frame, text="Opacity:", bg='#1a1a2e', fg='#aaaaaa', font=('Arial', 10)).pack(side=tk.LEFT)

        self.opacity_label = tk.Label(opacity_frame, text="92%", bg='#1a1a2e', fg='#4ecca3', font=('Arial', 10, 'bold'), width=4)
        self.opacity_label.pack(side=tk.RIGHT)

        opacity_slider = tk.Scale(
            opacity_frame,
            from_=50,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.opacity,
            command=lambda v: self._on_opacity_change(),
            bg='#1a1a2e',
            fg='#ffffff',
            troughcolor='#16213e',
            highlightthickness=0,
            resolution=1,
            length=150
        )
        opacity_slider.set(92)
        opacity_slider.pack(side=tk.RIGHT, padx=5)

        # === POSITION SECTION ===
        position_frame = tk.LabelFrame(main_frame, text="Position", bg='#1a1a2e', fg='#888888', font=('Arial', 9))
        position_frame.pack(fill=tk.X, pady=5)

        # Drag mode option
        drag_frame = tk.Frame(position_frame, bg='#1a1a2e')
        drag_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Checkbutton(
            drag_frame,
            text="Center horizontally (drag up/down only)",
            variable=self.vertical_only,
            command=self._apply_settings,
            bg='#1a1a2e',
            fg='#ffffff',
            selectcolor='#0f3460',
            activebackground='#1a1a2e',
            activeforeground='#ffffff',
            font=('Arial', 10)
        ).pack(side=tk.LEFT)

        drag_hint = tk.Label(
            position_frame,
            text="Uncheck to drag freely in all directions",
            font=('Arial', 8),
            bg='#1a1a2e',
            fg='#666666'
        )
        drag_hint.pack(pady=(0, 5))

        # === STATS SECTION ===
        stats_frame = tk.LabelFrame(main_frame, text="Vocabulary", bg='#1a1a2e', fg='#888888', font=('Arial', 9))
        stats_frame.pack(fill=tk.X, pady=5)

        self.stats_label = tk.Label(
            stats_frame,
            text="Words saved: 0",
            font=('Arial', 11),
            bg='#1a1a2e',
            fg='#4ecca3'
        )
        self.stats_label.pack(pady=5)

        vocab_btn_frame = tk.Frame(stats_frame, bg='#1a1a2e')
        vocab_btn_frame.pack(pady=5)

        tk.Button(
            vocab_btn_frame,
            text="📚 View My Words",
            font=('Arial', 10),
            command=self._open_vocab_viewer,
            bg='#4ecca3',
            fg='#000000',
            activebackground='#3db892',
            activeforeground='#000000',
            relief=tk.FLAT,
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            vocab_btn_frame,
            text="📤 Export CSV",
            font=('Arial', 10),
            command=self._export_csv_as,  # Changed to new method
            bg='#0f3460',
            fg='#ffffff',
            activebackground='#16213e',
            activeforeground='#ffffff',
            relief=tk.FLAT,
            padx=12,
            pady=5
        ).pack(side=tk.LEFT, padx=5)

        # Shortcuts hint
        tk.Label(
            main_frame,
            text="Drag subtitle to position • Space=Play/Pause • +/-=Sync",
            font=('Arial', 8),
            bg='#1a1a2e',
            fg='#444444'
        ).pack(side=tk.BOTTOM, pady=5)

    def _export_csv_as(self):
        """Export vocabulary to CSV with file picker"""
        if not self.vocabulary_saver or not self.vocabulary_saver.entries:
            from tkinter import messagebox
            messagebox.showwarning("No Data", "No vocabulary words to export.")
            return

        from tkinter import filedialog

        # Generate default filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"vocab_export_{timestamp}.csv"

        # Ask user for save location
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile=default_filename,
            title="Save Vocabulary CSV"
        )

        if not filepath:
            return  # User cancelled

        try:
            # Write the CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Header
                writer.writerow(['Word', 'Context Sentence', 'Movie', 'Timestamp', 'Date Saved'])
                
                # Rows
                for entry in self.vocabulary_saver.entries:
                    # Handle missing attributes gracefully
                    movie = os.path.basename(entry.movie_file) if getattr(entry, 'movie_file', None) else "Unknown"
                    writer.writerow([
                        entry.word,
                        entry.sentence,
                        movie,
                        getattr(entry, 'timestamp_formatted', ''),
                        getattr(entry, 'saved_at', '')
                    ])
            
            from tkinter import messagebox
            messagebox.showinfo("Export Successful", f"Successfully exported {len(self.vocabulary_saver.entries)} words to:\n{filepath}")
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Export Error", f"Failed to save file:\n{str(e)}")

    def _show_developer_info(self):
        """Show a window with developer's LinkedIn and Instagram links"""
        
        win = tk.Toplevel(self)
        win.title("About the Developer")
        win.configure(bg='#1a1a2e')
        
        # Center the popup relative to the control panel
        x = self.winfo_x() + 50
        y = self.winfo_y() + 100
        win.geometry(f"400x200+{x}+{y}")
        win.resizable(False, False)

        tk.Label(
            win,
            text="Developed by Mohamed Tantawi",
            font=('Arial', 12, 'bold'),
            fg='#4ecca3',
            bg='#1a1a2e'
        ).pack(pady=(20, 15))

        # LinkedIn
        link_url = "https://www.linkedin.com/in/mo-tantawi/"
        linkedin_frame = tk.Frame(win, bg='#1a1a2e')
        linkedin_frame.pack(pady=5)
        
        tk.Label(linkedin_frame, text="LinkedIn: ", font=('Arial', 10), fg='#aaaaaa', bg='#1a1a2e').pack(side=tk.LEFT)
        l_link = tk.Label(
            linkedin_frame, 
            text="View Profile", 
            font=('Arial', 10, 'underline'),
            fg='#0e76a8', 
            bg='#1a1a2e', 
            cursor="hand2"
        )
        l_link.pack(side=tk.LEFT)
        l_link.bind("<Button-1>", lambda e: webbrowser.open_new(link_url))

        # Instagram
        insta_url = "https://www.instagram.com/mohamed.tan6/"
        insta_frame = tk.Frame(win, bg='#1a1a2e')
        insta_frame.pack(pady=5)
        
        tk.Label(insta_frame, text="Instagram: ", font=('Arial', 10), fg='#aaaaaa', bg='#1a1a2e').pack(side=tk.LEFT)
        i_link = tk.Label(
            insta_frame, 
            text="View Profile", 
            font=('Arial', 10, 'underline'),
            fg='#e1306c', 
            bg='#1a1a2e', 
            cursor="hand2"
        )
        i_link.pack(side=tk.LEFT)
        i_link.bind("<Button-1>", lambda e: webbrowser.open_new(insta_url))

        # Close button
        tk.Button(
            win,
            text="Close",
            command=win.destroy,
            font=('Arial', 10),
            bg='#16213e',
            fg='#ffffff',
            relief=tk.FLAT,
            padx=15,
            pady=5
        ).pack(pady=20)

    def show_sync_offset_status(self, offset_ms):
        """Show a temporary label and hide the permanent label while it's visible"""
        if self._sync_offset_status_after_id:
            self.after_cancel(self._sync_offset_status_after_id)
            self._sync_offset_status_after_id = None
        
        msg = f"Subtitle offset: {offset_ms:+d}ms"
        
        # Ensure the status label exists
        if self._sync_offset_status_label is None:
            self._sync_offset_status_label = tk.Label(
                self._sync_offset_permanent_label.master,
                text="",
                font=('Arial', 10, 'bold'),
                bg='#1a1a2e',
                fg='#4ecca3'
            )
        
        # Hide permanent label while showing temporary
        self._sync_offset_permanent_label.pack_forget()
        self._sync_offset_status_label.config(text=msg)
        self._sync_offset_status_label.pack_forget()
        self._sync_offset_status_label.pack()
        self._sync_offset_status_label.lift()
        
        # Hide after 1.5 seconds
        self._sync_offset_status_after_id = self.after(1500, self._hide_sync_offset_status)

    def _hide_sync_offset_status(self):
        if self._sync_offset_status_label:
            self._sync_offset_status_label.pack_forget()
        # Restore permanent label
        self._sync_offset_permanent_label.pack(pady=(0, 2))
        self._sync_offset_status_after_id = None

    def _handle_sync_adjust(self, delta_ms):
        """Handle sync adjust button, call on_settings_change and show status"""
        if self.on_settings_change:
            self.on_settings_change({'sync_adjust': delta_ms, 'show_offset_status': True})
    
    def _load_file(self):
        """Open file dialog to load SRT"""
        from tkinter import filedialog
        
        filepath = filedialog.askopenfilename(
            title="Select SRT Subtitle File",
            filetypes=[
                ("SRT files", "*.srt"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            self.on_load_srt(filepath)
    
    def _choose_color(self):
        """Open color chooser dialog"""
        from tkinter import colorchooser
        
        color = colorchooser.askcolor(
            initialcolor=self.bg_color.get(),
            title="Choose Background Color"
        )
        
        if color[1]:
            self._set_color(color[1])
    
    def _set_color(self, color: str):
        """Set background color"""
        self.bg_color.set(color)
        self.color_preview.config(bg=color)
        self._apply_settings()
    
    def _on_font_change(self):
        """Font size changed"""
        self.font_label.config(text=str(self.font_size.get()))
        self._apply_settings()
    
    def _on_opacity_change(self):
        """Opacity changed"""
        self.opacity_label.config(text=f"{int(self.opacity.get())}%")
        self._apply_settings()
    
    def _apply_settings(self):
        """Apply settings to subtitle overlay"""
        if self.on_settings_change:
            settings = {
                'transparent': self.transparent_bg.get(),
                'bg_color': self.bg_color.get(),
                'font_size': self.font_size.get(),
                'opacity': self.opacity.get() / 100.0,
                'vertical_only': self.vertical_only.get(),
                'sync_mode': self.sync_mode.get()
            }
            self.on_settings_change(settings)
    
    def update_file_info(self, filename: str, subtitle_count: int):
        """Update the file info label"""
        self.file_label.config(
            text=f"📄 {filename} ({subtitle_count} subtitles)",
            fg='#4ecca3'
        )
    
    def update_stats(self, word_count: int, unique_count: int):
        """Update statistics display"""
        if not hasattr(self, 'stats_label') or self.stats_label is None:
            # Fallback: create a dummy label if UI not yet built
            self.stats_label = tk.Label(self, text="", font=('Arial', 11), bg='#1a1a2e', fg='#4ecca3')
            self.stats_label.pack()
        self.stats_label.config(
            text=f"Words saved: {word_count} ({unique_count} unique)"
        )
    
    def _open_vocab_viewer(self):
        """Open the vocabulary viewer window"""
        if self.vocabulary_saver is None:
            from tkinter import messagebox
            messagebox.showwarning("No Data", "No vocabulary data available.")
            return
        
        # If viewer exists and is open, bring to front
        if self.vocab_viewer and self.vocab_viewer.winfo_exists():
            self.vocab_viewer.lift()
            self.vocab_viewer.focus_force()
            self.vocab_viewer._refresh_list()
        else:
            # Create new viewer
            self.vocab_viewer = VocabularyViewer(self, self.vocabulary_saver)


class VocabularyViewer(tk.Toplevel):
    """
    Window to view and manage saved vocabulary words
    """
    
    def __init__(self, parent, vocabulary_saver):
        super().__init__(parent)
        
        self.vocab_saver = vocabulary_saver
        
        # Display mode: 'word', 'word_sentence', 'word_sentence_movie'
        self.display_mode = tk.StringVar(value='word_sentence')
        
        self.title("📚 My Vocabulary")
        self.geometry("700x550")
        self.configure(bg='#1a1a2e')
        self.resizable(True, True)
        
        self._create_ui()
        self._refresh_list()
    
    def _create_ui(self):
        """Create the vocabulary viewer UI"""
        # Top bar with display options
        top_frame = tk.Frame(self, bg='#1a1a2e')
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(
            top_frame,
            text="📚 My Saved Words",
            font=('Arial', 14, 'bold'),
            bg='#1a1a2e',
            fg='#ffffff'
        ).pack(side=tk.LEFT)
        
        # Refresh button
        tk.Button(
            top_frame,
            text="🔄 Refresh",
            font=('Arial', 10),
            command=self._refresh_list,
            bg='#16213e',
            fg='#ffffff',
            activebackground='#0f3460',
            activeforeground='#ffffff',
            relief=tk.FLAT,
            padx=10
        ).pack(side=tk.RIGHT, padx=5)
        
        # Display options frame
        options_frame = tk.LabelFrame(self, text="Display Options", bg='#1a1a2e', fg='#888888', font=('Arial', 9))
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        options_inner = tk.Frame(options_frame, bg='#1a1a2e')
        options_inner.pack(pady=8)
        
        radio_style = {
            'bg': '#1a1a2e',
            'fg': '#ffffff',
            'selectcolor': '#0f3460',
            'activebackground': '#1a1a2e',
            'activeforeground': '#ffffff',
            'font': ('Arial', 10)
        }
        
        tk.Radiobutton(
            options_inner,
            text="Word Only",
            variable=self.display_mode,
            value='word',
            command=self._refresh_list,
            **radio_style
        ).pack(side=tk.LEFT, padx=15)
        
        tk.Radiobutton(
            options_inner,
            text="Word + Sentence",
            variable=self.display_mode,
            value='word_sentence',
            command=self._refresh_list,
            **radio_style
        ).pack(side=tk.LEFT, padx=15)
        
        tk.Radiobutton(
            options_inner,
            text="Word + Sentence + Movie",
            variable=self.display_mode,
            value='word_sentence_movie',
            command=self._refresh_list,
            **radio_style
        ).pack(side=tk.LEFT, padx=15)
        
        # Search frame
        search_frame = tk.Frame(self, bg='#1a1a2e')
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(search_frame, text="🔍 Search:", bg='#1a1a2e', fg='#aaaaaa', font=('Arial', 10)).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._refresh_list())
        
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=('Arial', 11),
            bg='#16213e',
            fg='#ffffff',
            insertbackground='#ffffff',
            relief=tk.FLAT,
            width=30
        )
        search_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Stats label
        self.stats_label = tk.Label(
            search_frame,
            text="0 words",
            font=('Arial', 10),
            bg='#1a1a2e',
            fg='#4ecca3'
        )
        self.stats_label.pack(side=tk.RIGHT, padx=10)
        
        # Scrollable list frame
        list_frame = tk.Frame(self, bg='#1a1a2e')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(list_frame, bg='#0f0f23', highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg='#0f0f23')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)
        
        # Make canvas resize with window
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bottom buttons
        bottom_frame = tk.Frame(self, bg='#1a1a2e')
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        btn_style = {
            'font': ('Arial', 10),
            'bg': '#16213e',
            'fg': '#ffffff',
            'activebackground': '#0f3460',
            'activeforeground': '#ffffff',
            'relief': tk.FLAT,
            'padx': 15,
            'pady': 5
        }
        
        tk.Button(
            bottom_frame,
            text="🗑️ Delete Selected",
            command=self._delete_selected,
            **btn_style
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            bottom_frame,
            text="📋 Copy All to Clipboard",
            command=self._copy_to_clipboard,
            **btn_style
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            bottom_frame,
            text="✖ Close",
            command=self.destroy,
            **btn_style
        ).pack(side=tk.RIGHT, padx=5)
    
    def _on_canvas_configure(self, event):
        """Update canvas window width when canvas is resized"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _refresh_list(self):
        """Refresh the vocabulary list display"""
        # Clear existing items
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Get entries from vocabulary saver
        entries = self.vocab_saver.entries
        
        # Filter by search
        search_term = self.search_var.get().lower().strip()
        if search_term:
            entries = [e for e in entries if search_term in e.word.lower() or search_term in e.sentence.lower()]
        
        # Update stats
        self.stats_label.config(text=f"{len(entries)} words")
        
        # Track selected items
        self.selected_entries = set()
        self.entry_checkboxes = {}
        
        if not entries:
            no_words = tk.Label(
                self.scrollable_frame,
                text="No saved words yet.\nClick on words in subtitles to save them!",
                font=('Arial', 12),
                bg='#0f0f23',
                fg='#666666',
                pady=50
            )
            no_words.pack(fill=tk.X)
            return
        
        mode = self.display_mode.get()
        
        for i, entry in enumerate(entries):
            self._create_entry_widget(i, entry, mode)
    
    def _create_entry_widget(self, index: int, entry, mode: str):
        """Create a widget for a single vocabulary entry"""
        # Container for this entry
        entry_frame = tk.Frame(self.scrollable_frame, bg='#1a1a2e' if index % 2 == 0 else '#16213e')
        entry_frame.pack(fill=tk.X, pady=1)
        
        # Checkbox for selection
        var = tk.BooleanVar()
        cb = tk.Checkbutton(
            entry_frame,
            variable=var,
            bg=entry_frame['bg'],
            selectcolor='#0f3460',
            activebackground=entry_frame['bg']
        )
        cb.pack(side=tk.LEFT, padx=5)
        self.entry_checkboxes[index] = (var, entry)
        
        # Content frame
        content_frame = tk.Frame(entry_frame, bg=entry_frame['bg'])
        content_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=8)
        
        # Word (always shown, highlighted)
        word_label = tk.Label(
            content_frame,
            text=entry.word,
            font=('Arial', 13, 'bold'),
            bg=entry_frame['bg'],
            fg='#4ecca3'
        )
        word_label.pack(anchor='w')
        
        if mode in ['word_sentence', 'word_sentence_movie']:
            # Sentence with word highlighted
            sentence_text = entry.sentence
            sentence_label = tk.Label(
                content_frame,
                text=f"📝 \"{sentence_text}\"",
                font=('Arial', 10),
                bg=entry_frame['bg'],
                fg='#aaaaaa',
                wraplength=550,
                justify=tk.LEFT
            )
            sentence_label.pack(anchor='w', pady=(2, 0))
        
        if mode == 'word_sentence_movie':
            # Movie/file info and timestamp
            movie_name = os.path.basename(entry.movie_file) if entry.movie_file else "Unknown"
            info_text = f"🎬 {movie_name}  •  ⏱️ {entry.timestamp_formatted}  •  📅 {entry.saved_at[:10]}"
            
            info_label = tk.Label(
                content_frame,
                text=info_text,
                font=('Arial', 9),
                bg=entry_frame['bg'],
                fg='#666666'
            )
            info_label.pack(anchor='w', pady=(2, 0))
    
    def _delete_selected(self):
        """Delete selected vocabulary entries"""
        to_delete = []
        for idx, (var, entry) in self.entry_checkboxes.items():
            if var.get():
                to_delete.append(entry.word)
        
        if not to_delete:
            return
        
        # Confirm deletion
        from tkinter import messagebox
        if messagebox.askyesno("Confirm Delete", f"Delete {len(to_delete)} selected word(s)?"):
            for word in to_delete:
                self.vocab_saver.remove_word(word)
            self._refresh_list()
    
    def _copy_to_clipboard(self):
        """Copy displayed vocabulary to clipboard"""
        mode = self.display_mode.get()
        entries = self.vocab_saver.entries
        
        # Filter by search if active
        search_term = self.search_var.get().lower().strip()
        if search_term:
            entries = [e for e in entries if search_term in e.word.lower() or search_term in e.sentence.lower()]
        
        lines = []
        for entry in entries:
            if mode == 'word':
                lines.append(entry.word)
            elif mode == 'word_sentence':
                lines.append(f"{entry.word}\t{entry.sentence}")
            else:  # word_sentence_movie
                movie = os.path.basename(entry.movie_file) if entry.movie_file else "Unknown"
                lines.append(f"{entry.word}\t{entry.sentence}\t{movie}")
        
        text = "\n".join(lines)
        
        self.clipboard_clear()
        self.clipboard_append(text)
        
        from tkinter import messagebox
        messagebox.showinfo("Copied", f"Copied {len(entries)} entries to clipboard!")


# Testing
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    def on_word_click(word, sentence, timestamp):
        print(f"✓ Saved: '{word}' from '{sentence}'")
    
    overlay = SubtitleOverlay(
        root,
        on_word_click=on_word_click,
        font_size=32
    )
    
    # Show test subtitle
    overlay.update_subtitle(
        "Bonjour, comment allez-vous aujourd'hui?",
        5000,
        saved_words={'bonjour'}
    )
    
    print("VLC-style subtitle overlay test")
    print("- Drag the text to move it")
    print("- Click a word to save it (turns green)")
    print("- Yellow = hover, Green = saved")
    
    root.mainloop()