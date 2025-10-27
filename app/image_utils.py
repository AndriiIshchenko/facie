"""
Image utilities for validation, processing, and optimization.
"""
import logging
import uuid
from io import BytesIO
from pathlib import Path
from typing import Tuple

from PIL import Image
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

# Configuration
MAX_DIMENSION = 4096  # Maximum allowed dimension (width or height)
JPEG_QUALITY = 85  # JPEG compression quality (1-100)


class ImageProcessor:
    """
    Handles image validation, processing, and saving.
    """

    def __init__(self, media_dir: Path):
        """
        Initialize the image processor.

        Args:
            media_dir: Directory where images will be saved
        """
        self.media_dir = media_dir
        self.media_dir.mkdir(exist_ok=True)

    async def process_and_save_image(self, photo: UploadFile) -> Tuple[str, str]:
        """
        Process an uploaded image file and save it.

        Args:
            photo: The uploaded file

        Returns:
            Tuple of (unique_filename, photo_url)

        Raises:
            HTTPException: If validation fails or file cannot be saved
        """
        # Read file content
        content = await photo.read()

        # Validate and process image
        image = self._validate_image(content)
        image = self._convert_to_rgb(image)

        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}.jpg"
        file_path = self.media_dir / unique_filename

        # Save image
        self._save_image(image, file_path, photo.filename or "unknown")

        # Return filename and URL
        photo_url = f"/media/{unique_filename}"
        return unique_filename, photo_url

    def _validate_image(self, content: bytes) -> Image.Image:
        """
        Validate that the content is a valid image.

        Args:
            content: Raw file content

        Returns:
            PIL Image object

        Raises:
            HTTPException: If validation fails
        """
        try:
            # Verify it's a valid image
            image = Image.open(BytesIO(content))
            image.verify()

            # Re-open for processing (verify() closes the file)
            image = Image.open(BytesIO(content))
            original_format = image.format
            original_size = image.size

            logger.info(
                "Image validation successful: format=%s, size=%s",
                original_format,
                original_size
            )

            # Check dimensions
            if image.size[0] > MAX_DIMENSION or image.size[1] > MAX_DIMENSION:
                logger.warning("Image dimensions too large: %s", image.size)
                raise HTTPException(
                    status_code=400,
                    detail=f"Image dimensions too large. Maximum allowed: {MAX_DIMENSION}x{MAX_DIMENSION}"
                )

            return image

        except HTTPException:
            raise
        except Exception as e:
            logger.warning("Invalid image file uploaded: %s", str(e))
            raise HTTPException(
                status_code=400,
                detail=f"File must be a valid image: {str(e)}"
            )

    def _convert_to_rgb(self, image: Image.Image) -> Image.Image:
        """
        Convert image to RGB mode if needed (for JPEG compatibility).

        Args:
            image: PIL Image object

        Returns:
            RGB PIL Image object
        """
        if image.mode in ("RGBA", "LA", "P"):
            logger.info("Converting image from %s to RGB", image.mode)
            background = Image.new("RGB", image.size, (255, 255, 255))

            if image.mode == "P":
                image = image.convert("RGBA")

            # Paste with alpha mask if available
            if image.mode in ("RGBA", "LA"):
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)

            return background

        return image

    def _save_image(self, image: Image.Image, file_path: Path, original_filename: str) -> None:
        """
        Save image as optimized JPEG.

        Args:
            image: PIL Image object
            file_path: Path where to save the image
            original_filename: Original filename for logging

        Raises:
            HTTPException: If saving fails
        """
        try:
            image.save(file_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
            saved_size = file_path.stat().st_size

            logger.info(
                "Photo saved: %s (original: %s, format: %s, size: %s, bytes: %d)",
                file_path.name,
                original_filename,
                image.format,
                image.size,
                saved_size
            )

        except Exception as e:
            logger.error("Failed to save file: %s", str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Could not save file: {str(e)}"
            )


def get_image_processor(media_dir: Path) -> ImageProcessor:
    """
    Factory function to get an ImageProcessor instance.

    Args:
        media_dir: Directory where images will be saved

    Returns:
        ImageProcessor instance
    """
    return ImageProcessor(media_dir)
