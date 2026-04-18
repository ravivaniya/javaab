import io
import os
import json
import logging
import asyncio
from typing import Tuple
from PIL import Image, ImageOps, UnidentifiedImageError

from openai import AsyncAzureOpenAI
from app.models.schemas import ImageExtractionResult

logger = logging.getLogger(__name__)

# Constants
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
TIER_2_MODEL = os.getenv("AZURE_GPT4.1_MINI_DEPLOYMENT", "gpt-4.1-mini")

class ImageService:
    """
    Handles image validation, optimization, and OCR extraction leveraging GPT-4 Vision.
    """
    def __init__(self):
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_KEY", ""),
            api_version="2024-02-01"
        )

    def _sync_validate_image(self, image_bytes: bytes) -> bool:
        """Synchronous CPU-bound logic for validation."""
        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            logger.warning("Image validation failed: size exceeds 5MB")
            return False

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                if img.format not in ALLOWED_FORMATS:
                    logger.warning(f"Image validation failed: {img.format} not allowed.")
                    return False
                img.verify() # Check corruption
            return True
        except (UnidentifiedImageError, OSError) as e:
            logger.warning(f"Image validation failed: corrupted format. {e}")
            return False

    async def validate_image(self, image_bytes: bytes) -> bool:
        """
        Validates if the image is within size limits, correct format, and not corrupted.
        """
        return await asyncio.to_thread(self._sync_validate_image, image_bytes)

    def _sync_optimize_image(self, image_bytes: bytes) -> bytes:
        """Synchronous CPU-bound image manipulation."""
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Auto-rotate based on EXIF to correct orientation
            img = ImageOps.exif_transpose(img)
            
            # Convert RGBA/P to RGB for safe JPEG saving
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize holding aspect ratio. Max 1024x1024 bounding box.
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            output_buffer = io.BytesIO()
            quality = 85
            
            # Save strips EXIF automatically. Increment compression until < 1MB.
            # A 1024x1024 JPEG at quality=85 is typically ~100-200kb, safely passing 1MB.
            while True:
                output_buffer.seek(0)
                output_buffer.truncate()
                img.save(output_buffer, format="JPEG", quality=quality, optimize=True)
                
                size = output_buffer.tell()
                if size <= 1024 * 1024 or quality <= 10:
                    break
                
                quality -= 10
                
            return output_buffer.getvalue()

    async def optimize_image(self, image_bytes: bytes) -> bytes:
        """
        Optimizes image for bandwidth and AI processing.
        Strips EXIF, resizes to max 1024px width/height, compresses to <1MB JPEG.
        """
        return await asyncio.to_thread(self._sync_optimize_image, image_bytes)

    async def extract_question(self, image_base64: str) -> ImageExtractionResult:
        """
        Hits GPT-4.1-mini Vision to safely execute contextual OCR specifically 
        tuning to mathematical outputs, diagrams, and Indian languages.
        """
        prompt = (
            "You are an OCR assistant for Indian CBSE/GSEB students. "
            "Extract the exact question from this image.\n"
            "If math, convert to LaTeX. If diagram, describe and label all parts.\n"
            "If Hindi (Devanagari) or Gujarati script, preserve accurately.\n"
            "If image is unclear, say so specifically in the is_clear boolean.\n"
            "Output strictly as a JSON object matching this schema: "
            "{\"extracted_text\": \"...\", \"detected_language\": \"en/hi/gu\", \"detected_subject\": \"Math/Science/etc\", \"is_clear\": true/false}"
        )
        
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]}
        ]
        
        # Exponential backoff loop
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.openai_client.chat.completions.create(
                    model=TIER_2_MODEL,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000,
                    response_format={ "type": "json_object" }
                )
                
                output = response.choices[0].message.content
                if not output:
                    raise Exception("Empty response block")
                
                parsed = json.loads(output)
                return ImageExtractionResult(
                    extracted_text=parsed.get("extracted_text", ""),
                    detected_language=parsed.get("detected_language", "en"),
                    detected_subject=parsed.get("detected_subject", "Unknown"),
                    is_clear=parsed.get("is_clear", True)
                )
                
            except Exception as e:
                logger.error(f"OCR Extraction failed attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    logger.warning("Failing gracefully, flagging image as unclear.")
                    return ImageExtractionResult(
                        extracted_text="Error extracting data.",
                        detected_language="en",
                        detected_subject="Unknown",
                        is_clear=False
                    )
                
            await asyncio.sleep(2 ** attempt)

    async def close(self):
        await self.openai_client.close()
