import os
from flask import Flask, request, send_file, render_template
from PIL import Image, ImageResampling
import io
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Constants for photo sizes
PASSPORT_SIZE = (600, 600)  # 2x2 inches at 300 DPI
PAGE_SIZE = (1800, 1200)    # 4x6 inches at 300 DPI

def resize_and_crop(image, target_size):
    """Resize and crop the image to fit the target size."""
    width, height = image.size
    target_width, target_height = target_size

    # Calculate aspect ratio
    target_ratio = target_width / target_height
    image_ratio = width / height

    # Resize and crop
    if image_ratio > target_ratio:
        # Crop horizontally
        new_height = height
        new_width = int(height * target_ratio)
        left = (width - new_width) / 2
        top = 0
        right = (width + new_width) / 2
        bottom = height
    else:
        # Crop vertically
        new_width = width
        new_height = int(width / target_ratio)
        left = 0
        top = (height - new_height) / 2
        right = width
        bottom = (height + new_height) / 2

    image = image.crop((left, top, right, bottom))
    image = image.resize(target_size, Image.Resampling.LANCZOS)  # Use LANCZOS instead of ANTIALIAS
    return image

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
                return {"status": "error", "message": "No file uploaded"}, 400
            file = request.files["file"]
            if file.filename == "":
                return {"status": "error", "message": "No file selected"}, 400

            logging.info("File received, starting image processing")

            # Open and process the image
            input_image = Image.open(file.stream)

            # Resize and crop to 2x2 passport size
            passport_photo = resize_and_crop(input_image, PASSPORT_SIZE)

            # Create a 4x6 page with four 2x2 photos
            page_4x6 = create_4x6_page(passport_photo)

            # Save the images to bytes buffers
            passport_bytes = io.BytesIO()
            passport_photo.save(passport_bytes, format="PNG")
            passport_bytes.seek(0)

            page_bytes = io.BytesIO()
            page_4x6.save(page_bytes, format="PNG")
            page_bytes.seek(0)

            # Return the processed images as a zip file
            return send_file(
                page_bytes,
                mimetype="image/png",
                as_attachment=True,
                download_name="4x6_page.png",
            )

        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return {"status": "error", "message": str(e)}, 500

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
