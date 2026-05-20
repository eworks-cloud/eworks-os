"""
Generates SRT captions from script text using simple timing estimation.
No external API needed — estimates ~2.3 words per second reading pace.
"""
from __future__ import annotations
import re


class CaptionGenerator:
    WORDS_PER_SECOND = 2.3  # Average speaking pace

    def generate_srt(self, script_text: str, offset_seconds: float = 0.5) -> str:
        """
        Generate SRT caption file from script text.
        Splits into caption blocks of ~8 words each.
        Returns SRT-formatted string.
        """
        # Clean text
        text = re.sub(r'\s+', ' ', script_text.strip())
        words = text.split()
        blocks = []
        chunk_size = 8  # Words per caption block
        for i in range(0, len(words), chunk_size):
            blocks.append(' '.join(words[i:i + chunk_size]))

        srt_lines = []
        current_time = offset_seconds
        for idx, block in enumerate(blocks, 1):
            word_count = len(block.split())
            duration = word_count / self.WORDS_PER_SECOND
            start = self._format_time(current_time)
            end = self._format_time(current_time + duration)
            srt_lines.append(f'{idx}\n{start} --> {end}\n{block}\n')
            current_time += duration + 0.1  # 100ms gap
        return '\n'.join(srt_lines)

    def _format_time(self, seconds: float) -> str:
        """Format seconds to SRT time format HH:MM:SS,mmm"""
        ms = int((seconds % 1) * 1000)
        s = int(seconds)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
