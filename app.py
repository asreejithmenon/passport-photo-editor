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
    """Create a 4x6 page with four 2x2 passport photos."""
    page = Image.new("RGB", PAGE_SIZE, (255, 255, 255))  # White background
    photo_width, photo_height = PASSPORT_SIZE

    # Paste four photos on the page
    page.paste(image, (0, 0))  # Top-left
    page.paste(image, (photo_width, 0))  # Top-right
    page.paste(image, (0, photo_height))  # Bottom-left
    page.paste(image, (photo_width, photo_height))  # Bottom-right

    return page

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            if "file" not in request.files:
                return jsonify({"status": "error", "message": "No file uploaded"}), 400
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"status": "error", "message": "No file selected"}), 400

            logging.info("File received, starting image processing")

            # Remove background using Remove.bg API
            output_image = remove_background(file.stream)

            # Resize and crop to 2x2 passport size
            passport_photo = resize_and_crop(output_image, PASSPORT_SIZE)

            # Convert to white background
            white_bg = Image.new("RGB", passport_photo.size, (255, 255, 255))
            white_bg.paste(passport_photo, mask=passport_photo.split()[-1])

            # Create a 4x6 page with four 2x2 photos
            page_4x6 = create_4x6_page(white_bg)

            # Save the images to bytes buffers
            passport_bytes = io.BytesIO()
            white_bg.save(passport_bytes, format="PNG")
            passport_bytes.seek(0)

            page_bytes = io.BytesIO()
            page_4x6.save(page_bytes, format="PNG")
            page_bytes.seek(0)

            # Store the processed images in memory
            processed_images["single"] = passport_bytes
            processed_images["four"] = page_bytes

            # Return JSON with URLs for both images
            return jsonify({
                "status": "success",
                "single_photo_url": "/download/single",
                "four_photos_url": "/download/four",
            })

        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    return render_template("index.html")

@app.route("/download/single")
def download_single():
    """Endpoint to download the single 2x2 photo."""
    if "single" not in processed_images:
        return "File not found", 404
    return send_file(
        processed_images["single"],
        mimetype="image/png",
        as_attachment=True,
        download_name="2x2_passport_photo.png",
    )

@app.route("/download/four")
def download_four():
    """Endpoint to download the 4x6 page with four 2x2 photos."""
    if "four" not in processed_images:
        return "File not found", 404
    return send_file(
        processed_images["four"],
        mimetype="image/png",
        as_attachment=True,
        download_name="4x6_page.png",
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
