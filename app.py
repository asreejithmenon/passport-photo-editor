import os
from flask import Flask, request, send_file, render_template
from PIL import Image
import io
import logging
import requests

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Remove.bg API endpoint and key
REMOVE_BG_API_URL = "https://api.remove.bg/v1.0/removebg"
REMOVE_BG_API_KEY = "LpCckzHHasLpTMwYmj1r6uHj"  # Your Remove.bg API key

# Constants for photo sizes
PASSPORT_SIZE = (600, 600)  # 2x2 inches at 300 DPI
PAGE_SIZE = (1800, 1200)    # 4x6 inches at 300 DPI

# Determine the correct resampling filter based on Pillow version
try:
    from PIL import ImageResampling
    RESAMPLING_FILTER = ImageResampling.LANCZOS
except ImportError:
    # For older versions of Pillow (< 9.0.0), use the integer value for LANCZOS
    RESAMPLING_FILTER = Image.LANCZOS if hasattr(Image, 'LANCZOS') else 1  # 1 is the integer code for LANCZOS

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

def resize_and_crop(image, max_size=1024):
    """Resize the image to a maximum dimension while maintaining aspect ratio."""
    width, height = image.size
    if max(width, height) > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        return image.resize((new_width, new_height), RESAMPLING_FILTER)
    return image

# ... (rest of your code remains unchanged)
