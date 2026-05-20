"""
Generates YouTube thumbnails using FAL.ai.
Optimized for 1280x720 YouTube thumbnail format.
"""
from __future__ import annotations
import logging
from eworks.agents.publisher.image_generator import ImageGenerator


class ThumbnailGenerator:
    def __init__(self):
        self.image_gen = ImageGenerator()
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_youtube_thumbnail(self, title: str, topic: str) -> str:
        """
        Generate a YouTube thumbnail image.
        Returns local file path.
        """
        prompt = (
            f'YouTube video thumbnail for: {title}. '
            f'Topic: {topic}. '
            f'Professional, high contrast, eye-catching design. '
            f'Bold visual, minimal text space, tech/AI theme. '
            f'16:9 landscape format, vibrant colors, modern style.'
        )
        return self.image_gen.generate(
            prompt,
            size='landscape_16_9',
            filename=f'thumbnail_{hash(title) % 100000}',
        )

    def generate_reel_cover(self, topic: str) -> str:
        """
        Generate a Reel/Short cover image (9:16 portrait).
        """
        prompt = (
            f'Social media video cover for: {topic}. '
            f'Eye-catching, vertical 9:16 format, bold design, '
            f'professional AI/tech aesthetic, minimal text space.'
        )
        return self.image_gen.generate(
            prompt,
            size='portrait_16_9',
            filename=f'reel_cover_{hash(topic) % 100000}',
        )
