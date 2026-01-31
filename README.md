# VLC Subtitle Learner

Learn languages while watching movies without pausing! This app displays subtitles from `.srt` files in a floating overlay window, allowing you to click on unknown words to save them for later review.

## 🎯 What It Does

- **Floating subtitle overlay** that stays on top of VLC
- **Clickable words** - click any word you don't know
- **Auto-saves vocabulary** with full sentence context and timestamp
- **Manual sync** - adjust timing with keyboard shortcuts
- **Export to CSV** for importing into Anki or other flashcard apps

## 🚀 Quick Start

### 1. Run the App

```bash
python main.py
```

### 2. Load Your Subtitle File
- Click "📂 Load SRT File" in the control panel
- Select your `.srt` subtitle file

### 3. Start Your Movie in VLC
- Open VLC and load your movie
- **Turn OFF VLC's built-in subtitles** (V key or Subtitle menu)

### 4. Sync and Start
- When the movie starts, press **Space** or click **Start**
- Use **+/-** keys to adjust timing if subtitles are out of sync

### 5. Click to Learn
- Click on any word you don't know
- The word turns green ✓ and is saved automatically

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause subtitle sync |
| `+` or `=` | Subtitles late? Move forward (+500ms) |
| `-` | Subtitles early? Move backward (-500ms) |
| `←` `→` | Fine-tune sync (±100ms) |
| `F` | Cycle font size |
| `R` | Reset to beginning |
| `Esc` | Hide/show overlay |

## 📁 Project Structure

```
VLC-sub/
├── main.py              # Main application entry point
├── srt_parser.py        # SRT file parsing logic
├── sync_engine.py       # Timing and synchronization
├── subtitle_overlay.py  # UI components (overlay + control panel)
├── vocabulary_saver.py  # Save/export vocabulary
├── vocabulary.json      # Your saved words (auto-created)
└── README.md           # This file
```

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      main.py                                │
│                   (VLCSubtitleLearner)                      │
│  Integrates all components, handles keyboard, update loop   │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ srt_parser  │ │ sync_engine │ │  subtitle   │ │ vocabulary  │
│             │ │             │ │  _overlay   │ │   _saver    │
│ Parse .srt  │ │ Timer-based │ │ Floating UI │ │ JSON/CSV    │
│ files into  │ │ playback    │ │ Clickable   │ │ storage     │
│ Subtitle    │ │ with offset │ │ words       │ │             │
│ objects     │ │ adjustment  │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Data Flow

1. **SRT Parsing**: File → `parse_srt_file()` → List of `Subtitle` objects
2. **Sync Engine**: Wall clock time + offset → current subtitle position
3. **UI Update**: 100ms loop checks for subtitle changes, updates display
4. **Word Click**: Click → save to JSON with context → visual feedback

### Sync Logic

```python
# User presses Start when movie starts
start_time = wall_clock_now

# Every 100ms:
elapsed_ms = (wall_clock_now - start_time) * 1000
adjusted_ms = elapsed_ms + user_offset  # User can adjust with +/-

# Find subtitle where: start_ms <= adjusted_ms <= end_ms
current_subtitle = binary_search(subtitles, adjusted_ms)
```

## 📊 Vocabulary File Format

Your saved words are stored in `vocabulary.json`:

```json
{
  "metadata": {
    "created": "2025-01-01T10:00:00",
    "last_updated": "2025-01-01T12:30:00",
    "total_words": 42
  },
  "entries": [
    {
      "word": "bonjour",
      "sentence": "Bonjour, comment allez-vous?",
      "timestamp_ms": 5000,
      "timestamp_formatted": "00:00:05",
      "movie_file": "french_movie.srt",
      "saved_at": "2025-01-01T10:05:23"
    }
  ]
}
```

## 🎴 Export to Anki

1. Click "📤 Export to CSV" in the control panel
2. Creates `vocabulary.csv` with columns:
   - Word
   - Sentence (context)
   - Timestamp
   - Movie
   - Saved At
3. Import into Anki using File → Import

## 🔧 Customization

Edit the `DEFAULT_CONFIG` in `main.py`:

```python
DEFAULT_CONFIG = {
    'font_size': 24,           # Subtitle font size
    'bg_color': '#1a1a2e',     # Background color
    'fg_color': '#ffffff',     # Text color
    'opacity': 0.92,           # Window transparency
    'overlay_width': 900,      # Overlay window width
    'overlay_height': 120,     # Overlay window height
    'sync_step_ms': 500,       # +/- adjustment step
    'update_interval_ms': 100, # Subtitle check frequency
}
```

## 💡 Tips

1. **Position the overlay** by dragging it to the bottom of your screen
2. **Start sync precisely** - press Space exactly when the first spoken word begins
3. **Fine-tune with arrow keys** for precise sync (±100ms)
4. **Don't click every word** - focus on words you truly don't know
5. **Review saved words** after watching by opening `vocabulary.json`

## 🐛 Troubleshooting

**Subtitles not showing?**
- Make sure you loaded an SRT file
- Press Space to start playback
- Check the time display is advancing

**Encoding issues?**
- The parser tries UTF-8, UTF-8-BOM, Latin-1, and CP1252 automatically
- If still failing, convert your SRT to UTF-8 using Notepad++

**Overlay not visible?**
- Press Esc to toggle visibility
- Check if it's behind other windows

## 📝 Requirements

- Python 3.10+ (for type hints with `|`)
- Tkinter (included with Python on Windows)
- No external dependencies!

## 🎬 Enjoy learning languages while watching movies!
