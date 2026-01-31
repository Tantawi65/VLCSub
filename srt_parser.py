"""
SRT Subtitle Parser
Parses .srt files into structured subtitle data
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Subtitle:
    """Represents a single subtitle entry"""
    index: int
    start_ms: int  # Start time in milliseconds
    end_ms: int    # End time in milliseconds
    text: str      # The subtitle text (may contain multiple lines)
    
    @property
    def start_formatted(self) -> str:
        """Return start time as HH:MM:SS,mmm"""
        return ms_to_timestamp(self.start_ms)
    
    @property
    def end_formatted(self) -> str:
        """Return end time as HH:MM:SS,mmm"""
        return ms_to_timestamp(self.end_ms)


def timestamp_to_ms(timestamp: str) -> int:
    """
    Convert SRT timestamp to milliseconds
    Format: HH:MM:SS,mmm or HH:MM:SS.mmm
    """
    # Handle both comma and period as decimal separator
    timestamp = timestamp.replace(',', '.')
    
    # Parse hours:minutes:seconds.milliseconds
    match = re.match(r'(\d{1,2}):(\d{2}):(\d{2})\.(\d{3})', timestamp)
    if not match:
        raise ValueError(f"Invalid timestamp format: {timestamp}")
    
    hours, minutes, seconds, milliseconds = map(int, match.groups())
    
    total_ms = (
        hours * 3600000 +      # Hours to ms
        minutes * 60000 +       # Minutes to ms
        seconds * 1000 +        # Seconds to ms
        milliseconds            # Already in ms
    )
    
    return total_ms


def ms_to_timestamp(ms: int) -> str:
    """Convert milliseconds back to SRT timestamp format"""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_srt_file(filepath: str, encoding: str = 'utf-8') -> List[Subtitle]:
    """
    Parse an SRT file and return a list of Subtitle objects
    
    Args:
        filepath: Path to the .srt file
        encoding: File encoding (default utf-8, try 'latin-1' if issues)
    
    Returns:
        List of Subtitle objects sorted by start time
    """
    subtitles = []
    
    # Try different encodings if utf-8 fails
    encodings_to_try = [encoding, 'utf-8-sig', 'latin-1', 'cp1252']
    
    content = None
    for enc in encodings_to_try:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue
    
    if content is None:
        raise ValueError(f"Could not decode file with any supported encoding")
    
    # Remove BOM if present
    content = content.lstrip('\ufeff')
    
    # Split into subtitle blocks (separated by blank lines)
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        lines = block.split('\n')
        if len(lines) < 3:
            continue
        
        try:
            # First line: subtitle index
            index = int(lines[0].strip())
            
            # Second line: timestamps
            timestamp_line = lines[1].strip()
            timestamp_match = re.match(
                r'(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})',
                timestamp_line
            )
            
            if not timestamp_match:
                continue
            
            start_time = timestamp_match.group(1)
            end_time = timestamp_match.group(2)
            
            # Remaining lines: subtitle text
            text = '\n'.join(lines[2:]).strip()
            
            # Remove HTML tags if present (like <i>, <b>, etc.)
            text = re.sub(r'<[^>]+>', '', text)
            
            subtitle = Subtitle(
                index=index,
                start_ms=timestamp_to_ms(start_time),
                end_ms=timestamp_to_ms(end_time),
                text=text
            )
            
            subtitles.append(subtitle)
            
        except (ValueError, IndexError) as e:
            # Skip malformed blocks
            continue
    
    # Sort by start time (in case file is not properly ordered)
    subtitles.sort(key=lambda s: s.start_ms)
    
    return subtitles


def get_subtitle_at_time(subtitles: List[Subtitle], current_ms: int) -> Optional[Subtitle]:
    """
    Find the subtitle that should be displayed at the given time
    
    Uses binary search for efficiency with large subtitle files
    """
    if not subtitles:
        return None
    
    # Binary search for efficiency
    left, right = 0, len(subtitles) - 1
    
    while left <= right:
        mid = (left + right) // 2
        sub = subtitles[mid]
        
        if sub.start_ms <= current_ms <= sub.end_ms:
            return sub
        elif current_ms < sub.start_ms:
            right = mid - 1
        else:
            left = mid + 1
    
    return None


# Testing
if __name__ == "__main__":
    # Test with a sample SRT content
    sample_srt = """1
00:00:01,000 --> 00:00:04,000
Hello, welcome to the movie.

2
00:00:05,500 --> 00:00:08,200
This is the second subtitle.
It has two lines.

3
00:00:10,000 --> 00:00:12,500
<i>This has italic tags</i>
"""
    
    # Write test file
    with open("test.srt", "w", encoding="utf-8") as f:
        f.write(sample_srt)
    
    # Parse and display
    subs = parse_srt_file("test.srt")
    for sub in subs:
        print(f"[{sub.start_formatted} --> {sub.end_formatted}]")
        print(f"  {sub.text}")
        print()
    
    # Test time lookup
    print(f"At 2000ms: {get_subtitle_at_time(subs, 2000)}")
    print(f"At 6000ms: {get_subtitle_at_time(subs, 6000)}")
    print(f"At 9000ms: {get_subtitle_at_time(subs, 9000)}")
