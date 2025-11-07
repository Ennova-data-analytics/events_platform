from PIL import Image
from rembg import remove
import io
from typing import BinaryIO
import logging

logger = logging.getLogger(__name__)

class ImageProcessingService:
    @staticmethod
    def optimize_logo_only(
        file_obj: BinaryIO,
        max_width: int = 800,
        max_height: int = 400,
        output_format: str = 'PNG'
    ) -> tuple[io.BytesIO, str]:
        """
        Simple optimisation without background removal.
        Just resize, add padding, and optimise.

        """
        try:
            input_image = Image.open(file_obj)

            if input_image.mode != 'RGBA':
                input_image = input_image.convert('RGBA')

            input_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            width, height = input_image.size
            padding = int(min(width, height) * 0.1)
            new_width = width + 2 * padding
            new_height = height + 2 * padding

            final_image = Image.new('RGBA', (new_width, new_height), (255, 255, 255, 0))

            x_offset = (new_width - width) // 2
            y_offset = (new_height - height) // 2
            final_image.paste(input_image, (x_offset, y_offset), input_image)

            output_buffer = io.BytesIO()
            final_image.save(output_buffer, format=output_format, optimize=True, quality=95)
            output_buffer.seek(0)

            content_type = f'image/{output_format.lower()}'
            logger.info(f"Logo optimised: {new_width}x{new_height}")
            return output_buffer, content_type

        except Exception as e:
            logger.error(f"Error optimizing logo: {str(e)}")
            file_obj.seek(0)
            return file_obj, 'image/png'

    @staticmethod
    def process_sponsor_logo(
        file_obj: BinaryIO,
        max_width: int = 800,
        max_height: int = 400,
        output_format: str = 'PNG',
        aggressive_cleaning: bool = True,
        remove_bg: bool = True
    ) -> tuple[io.BytesIO, str]:
        """
        Process a sponsor logo:
        1. Remove background (optional)
        2. Resize while maintaining aspect ratio
        3. Add padding if needed
        4. Convert to PNG with transparency
        """
        try:
            if not remove_bg:
                return ImageProcessingService.optimize_logo_only(
                    file_obj, max_width, max_height, output_format
                )
            input_image = Image.open(file_obj)

            if input_image.mode not in ('RGB', 'RGBA'):
                input_image = input_image.convert('RGBA')

            img_byte_arr = io.BytesIO()
            input_image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            logger.info("Removing background from sponsor logo...")
            output_data = remove(
                img_byte_arr.read(),
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10,
                alpha_matting_erode_size=10
            )

            processed_image = Image.open(io.BytesIO(output_data))

            if processed_image.mode != 'RGBA':
                processed_image = processed_image.convert('RGBA')

            if aggressive_cleaning:
                pixels = processed_image.load()
                width, height = processed_image.size

                for y in range(height):
                    for x in range(width):
                        r, g, b, a = pixels[x, y]
                        if a < 30:
                            pixels[x, y] = (r, g, b, 0)
                        elif a < 200:
                            pixels[x, y] = (r, g, b, min(255, int(a * 1.3)))

            bbox = processed_image.getbbox()

            if bbox:
                processed_image = processed_image.crop(bbox)

            processed_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            final_width, final_height = processed_image.size

            padding = int(min(final_width, final_height) * 0.1)
            new_width = final_width + 2 * padding
            new_height = final_height + 2 * padding

            final_image = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))

            x_offset = (new_width - final_width) // 2
            y_offset = (new_height - final_height) // 2
            final_image.paste(processed_image, (x_offset, y_offset), processed_image)

            output_buffer = io.BytesIO()
            final_image.save(
                output_buffer,
                format=output_format,
                optimize=True,
                quality=95
            )
            output_buffer.seek(0)

            content_type = f'image/{output_format.lower()}'

            logger.info(f"Logo processed successfully: {new_width}x{new_height}")
            return output_buffer, content_type

        except Exception as e:
            logger.error(f"Error processing sponsor logo: {str(e)}")
            file_obj.seek(0)
            return file_obj, 'image/png'

    @staticmethod
    def validate_image(file_obj: BinaryIO, max_size_mb: int = 10) -> tuple[bool, str]:
        """
        Validate if the uploaded file is a valid image
        """
        try:
            file_obj.seek(0, 2)  
            file_size = file_obj.tell()
            file_obj.seek(0) 

            if file_size > max_size_mb * 1024 * 1024:
                return False, f"File size exceeds {max_size_mb}MB limit"

            img = Image.open(file_obj)
            img.verify()
            file_obj.seek(0)

            allowed_formats = ['JPEG', 'JPG', 'PNG', 'GIF', 'WEBP', 'BMP']
            if img.format not in allowed_formats:
                return False, f"Invalid image format. Allowed: {', '.join(allowed_formats)}"

            if img.width < 100 or img.height < 100:
                return False, "Image dimensions too small (minimum 100x100px)"

            return True, ""

        except Exception as e:
            return False, f"Invalid image file: {str(e)}"


image_processing_service = ImageProcessingService()
