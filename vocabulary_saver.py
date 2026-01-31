"""
Vocabulary Saver
Handles saving clicked words to JSON for later review
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class VocabularyEntry:
    """A single vocabulary entry"""
    word: str                    # The clicked word
    sentence: str                # Full subtitle sentence for context
    timestamp_ms: int            # When in the video this appeared
    timestamp_formatted: str     # Human readable timestamp
    movie_file: str              # Which movie/subtitle file
    saved_at: str                # When the user saved this word
    notes: str = ""              # Optional user notes (for future feature)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> 'VocabularyEntry':
        return VocabularyEntry(**data)


class VocabularySaver:
    """
    Manages vocabulary storage
    
    Saves to a JSON file with the structure:
    {
        "metadata": {
            "created": "...",
            "last_updated": "...",
            "total_words": 123
        },
        "entries": [
            { word entry },
            ...
        ]
    }
    """
    
    def __init__(self, save_path: str = "vocabulary.json"):
        self.save_path = save_path
        self.entries: List[VocabularyEntry] = []
        self.metadata: Dict = {}
        
        # Load existing data if file exists
        self._load()
    
    def _load(self):
        """Load existing vocabulary from file"""
        if not os.path.exists(self.save_path):
            self.metadata = {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_words": 0
            }
            return
        
        try:
            with open(self.save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get("metadata", {})
            self.entries = [
                VocabularyEntry.from_dict(e) 
                for e in data.get("entries", [])
            ]
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load vocabulary file: {e}")
            self.metadata = {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_words": 0
            }
            self.entries = []
    
    def _save(self):
        """Save vocabulary to file"""
        self.metadata["last_updated"] = datetime.now().isoformat()
        self.metadata["total_words"] = len(self.entries)
        
        data = {
            "metadata": self.metadata,
            "entries": [e.to_dict() for e in self.entries]
        }
        
        # Create backup before overwriting
        if os.path.exists(self.save_path):
            backup_path = self.save_path + ".backup"
            try:
                os.replace(self.save_path, backup_path)
            except OSError:
                pass
        
        with open(self.save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_word(
        self,
        word: str,
        sentence: str,
        timestamp_ms: int,
        movie_file: str = ""
    ) -> VocabularyEntry:
        """
        Add a new word to vocabulary
        
        Args:
            word: The clicked word
            sentence: Full subtitle text for context
            timestamp_ms: Position in video (milliseconds)
            movie_file: Name of the subtitle/movie file
        
        Returns:
            The created VocabularyEntry
        """
        # Clean the word
        word = word.strip().lower()
        
        # Format timestamp
        total_seconds = timestamp_ms // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        timestamp_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        entry = VocabularyEntry(
            word=word,
            sentence=sentence.strip(),
            timestamp_ms=timestamp_ms,
            timestamp_formatted=timestamp_formatted,
            movie_file=movie_file,
            saved_at=datetime.now().isoformat()
        )
        
        self.entries.append(entry)
        self._save()
        
        return entry
    
    def get_all_words(self) -> List[str]:
        """Get list of all saved words"""
        return [e.word for e in self.entries]
    
    def get_unique_words(self) -> List[str]:
        """Get list of unique saved words"""
        return list(set(self.get_all_words()))
    
    def get_entries_for_word(self, word: str) -> List[VocabularyEntry]:
        """Get all entries for a specific word"""
        word = word.lower()
        return [e for e in self.entries if e.word == word]
    
    def get_recent_entries(self, count: int = 10) -> List[VocabularyEntry]:
        """Get most recently added entries"""
        return self.entries[-count:][::-1]
    
    def word_exists(self, word: str) -> bool:
        """Check if word is already saved"""
        word = word.lower()
        return any(e.word == word for e in self.entries)
    
    def remove_word(self, word: str) -> bool:
        """
        Remove all entries for a word
        
        Args:
            word: The word to remove
            
        Returns:
            True if word was found and removed, False otherwise
        """
        word = word.lower()
        original_count = len(self.entries)
        self.entries = [e for e in self.entries if e.word != word]
        
        if len(self.entries) < original_count:
            self._save()
            return True
        return False
    
    def get_word_count(self, word: str) -> int:
        """Get how many times a word has been saved"""
        word = word.lower()
        return sum(1 for e in self.entries if e.word == word)
    
    def export_to_csv(self, csv_path: str = None):
        """Export vocabulary to CSV for external tools (Anki, etc.)"""
        if csv_path is None:
            csv_path = self.save_path.replace('.json', '.csv')
        
        import csv
        
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Word', 'Sentence', 'Timestamp', 'Movie', 'Saved At'])
            
            for entry in self.entries:
                writer.writerow([
                    entry.word,
                    entry.sentence,
                    entry.timestamp_formatted,
                    entry.movie_file,
                    entry.saved_at
                ])
        
        return csv_path
    
    def get_stats(self) -> dict:
        """Get vocabulary statistics"""
        words = self.get_all_words()
        unique = self.get_unique_words()
        
        return {
            "total_saves": len(words),
            "unique_words": len(unique),
            "most_saved": self._get_most_saved(5),
            "by_movie": self._get_by_movie()
        }
    
    def _get_most_saved(self, count: int) -> List[tuple]:
        """Get most frequently saved words"""
        from collections import Counter
        word_counts = Counter(self.get_all_words())
        return word_counts.most_common(count)
    
    def _get_by_movie(self) -> Dict[str, int]:
        """Get word counts grouped by movie"""
        by_movie = {}
        for entry in self.entries:
            movie = entry.movie_file or "Unknown"
            by_movie[movie] = by_movie.get(movie, 0) + 1
        return by_movie


# Testing
if __name__ == "__main__":
    # Test vocabulary saver
    saver = VocabularySaver("test_vocabulary.json")
    
    # Add some test words
    saver.add_word(
        word="bonjour",
        sentence="Bonjour, comment allez-vous?",
        timestamp_ms=5000,
        movie_file="test_movie.srt"
    )
    
    saver.add_word(
        word="merci",
        sentence="Merci beaucoup pour votre aide.",
        timestamp_ms=15000,
        movie_file="test_movie.srt"
    )
    
    saver.add_word(
        word="bonjour",  # Duplicate
        sentence="Bonjour mon ami!",
        timestamp_ms=30000,
        movie_file="test_movie.srt"
    )
    
    # Display stats
    print("Vocabulary Stats:")
    stats = saver.get_stats()
    print(f"  Total saves: {stats['total_saves']}")
    print(f"  Unique words: {stats['unique_words']}")
    print(f"  Most saved: {stats['most_saved']}")
    
    # Export to CSV
    csv_file = saver.export_to_csv()
    print(f"\nExported to: {csv_file}")
    
    # Display recent entries
    print("\nRecent entries:")
    for entry in saver.get_recent_entries():
        print(f"  {entry.word}: \"{entry.sentence}\" @ {entry.timestamp_formatted}")
