"""
FAL.ai image generation for social media posts.
Generates AI images using Flux Schnell model.
"""
from __future__ import annotations
import os
import logging
import requests
import time
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

FAL_API_BASE = "https://fal.run"
FAL_IMAGE_MODEL = "fal-ai/flux/schnell"


class ImageGenerator:
    """
    Generates images via FAL.ai Flux model.
    Supports single image and batch generation for carousels.
    """

    def __init__(self):
        self.api_key = os.environ.get("FAL_KEY", "")
        self.output_dir = Path("data/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, prompt: str, size: str = "square_hd", filename: str = None) -> str:
        """
        Generate a single image.

        Args:
            prompt: Image description
            size: "square_hd" (1:1), "portrait_4_3", "landscape_4_3",
                  "portrait_16_9", "landscape_16_9"
            filename: Optional output filename (without extension)

        Returns:
            Local file path to downloaded image
        """
        if not self.api_key:
            raise ValueError("FAL_KEY not set in environment")

        payload = {
            "prompt": prompt,
            "image_size": size,
            "num_inference_steps": 4,
            "num_images": 1,
            "enable_safety_checker": True,
        }

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

        self.logger.info("Generating image: %s...", prompt[:60])
        resp = requests.post(
            f"{FAL_API_BASE}/{FAL_IMAGE_MODEL}",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        images = data.get("images", [])
        if not images:
            raise RuntimeError(f"No images in FAL response: {data}")

        image_url = images[0].get("url", "")
        if not image_url:
            raise RuntimeError("No image URL in FAL response")

        # Download image
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = filename or f"img_{ts}"
        ext = ".png" if ".png" in image_url else ".jpg"
        local_path = self.output_dir / f"{fname}{ext}"

        img_resp = requests.get(image_url, timeout=60)
        img_resp.raise_for_status()
        local_path.write_bytes(img_resp.content)

        self.logger.info("Image saved: %s", local_path)
        return str(local_path)

    def generate_batch(self, prompts: list[str], size: str = "square_hd") -> list[str]:
        """
        Generate multiple images (for carousels).
        Returns list of local file paths.
        """
        paths = []
        for i, prompt in enumerate(prompts):
            path = self.generate(prompt, size=size, filename=f"carousel_{i}_{int(time.time())}")
            paths.append(path)
            time.sleep(1)  # Rate limit between requests
        return paths

    def generate_for_post(self, topic: str, platform: str = "linkedin", content_type: str = "image") -> str:
        """
        Generate image with platform-optimized prompt and size.
        LinkedIn: landscape_4_3 for images, square_hd for single posts
        Instagram: square_hd for feed, portrait_4_3 for stories
        """
        sizes = {
            "linkedin_image": "landscape_4_3",
            "linkedin_carousel": "square_hd",
            "instagram_image": "square_hd",
            "instagram_carousel": "square_hd",
            "instagram_reel": "portrait_16_9",
        }
        key = f"{platform}_{content_type}"
        size = sizes.get(key, "square_hd")

        # Enhance prompt for professional AI/tech content
        enhanced_prompt = (
            f"Professional business illustration for social media: {topic}. "
            f"Modern, clean design, tech/AI theme, blue and white color palette, "
            f"minimal text, high quality, corporate style."
        )
        return self.generate(enhanced_prompt, size=size)
