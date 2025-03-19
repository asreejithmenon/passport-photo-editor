import os
from flask import Flask, request, send_file, render_template, jsonify
from PIL import Image
import io
import logging
import requests

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Remove.bg API endpoint and key
REMOVE_BG_API_URL = "https://api.remove.bg/v1.0/removebg"
REMOVE_BG_API_KEY = "LpCckzHHasLpTMwYmj1r6uHj"  # Replace with your Remove.bg API key

# Constants for photo sizes
PASSPORT_SIZE = (600, 600)  # 2x2 inches at 300 DPI
PAGE_SIZE = (1800, 1200)    # 4x6 inches at 300 DPI

# Backward compatibility for Pillow
try:
    from PIL import ImageResampling
    RESAMPLING_FILTER = ImageResampling.LANCZOS
except ImportError:
    # Fallback for older Pillow versions (pre-9.1.0)
    RESAMPLING_FILTER = Image.LANCZOS  # Use LANCZOS directly if ImageResampling is not available

# Temporary storage for processed images
processed_images = {}

def remove_background(image_stream):
    """Remove the background using the Remove.bg API."""
    try:
        response = requests.post(
            REMOVE_BG_API_URL,
            files={"image_file": image_stream},
            headers={"X-Api-Key": REMOVE_BG_API_KEY},
        )
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        elif response.status_code == 402:
            raise Exception("API limit reached. Please upgrade your Remove.bg plan.")
        else:
            raise Exception(f"Remove.bg API error: {response.text}")
    except Exception as e:
        logging.error(f"Error calling Remove.bg API: {e}")
        raise

def resize_and_crop(image, size):
    """Resize and crop the image to the specified size."""
    width, height = image.size
    target_width, target_height = size

    # Calculate aspect ratio
    target_ratio = target_width / target_height
    image_ratio = width / height

    # Crop and resize
    if image_ratio > target_ratio:
        # Crop width
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        right = left + new_width
        image = image.crop((left, 0, right, height))
    else:
        # Crop height
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        bottom = top + new_height
        image = image.crop((0, top, width, bottom))

    # Resize to target size
    return image.resize(size, RESAMPLING_FILTER)

def create_4x6_page(image):
    """Create a 4x6 page with four 2
