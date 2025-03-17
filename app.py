import os
from flask import Flask, request, send_file, render_template
from rembg import remove
from PIL import Image
import io
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Constants for photo sizes
PASSPORT_SIZE = (600, 600)  # 2x2 inches at 300 DPI
PAGE_SIZE = (1800, 1200)    # 4x6 inches at 300 DPI

# Backward compatibility for Pillow
try:
    from PIL import ImageResampling
    RESAMPLING_FILTER = ImageResampling.LANCZOS
except ImportError:
    RESAMPLING_FILTER = Image.ANTIALIAS  # Fallback for older Pillow versions

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

            # Open and resize the image
            input_image = Image.open(file.stream)
            input_image = resize_and_crop(input_image)

            # Remove background using a smaller model (u2netp)
            output_image = remove(input_image, model_name="u2netp")

            # Convert to white background
            white_bg = Image.new("RGB", output_image.size, (255, 255, 255))
            white_bg.paste(output_image, mask=output_image.split()[-1])

            # Create a 4x6 page with four 2x2 photos
            page_4x6 = create_4x6_page(white_bg)

            # Save the images to bytes buffers
            passport_bytes = io.BytesIO()
            white_bg.save(passport_bytes, format="PNG")
            passport_bytes.seek(0)

            page_bytes = io.BytesIO()
            page_4x6.save(page_bytes, format="PNG")
            page_bytes.seek(0)

            # Clear memory
            del input_image, output_image, white_bg, page_4x6

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
