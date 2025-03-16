from flask import Flask, request, send_file, render_template
from rembg import remove
from PIL import Image
import io
import logging
import os

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

def resize_image(image, max_size=1024):
    """Resize the image to a maximum dimension while maintaining aspect ratio."""
    width, height = image.size
    if max(width, height) > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        return image.resize((new_width, new_height), Image.ANTIALIAS)
    return image

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
            input_image = resize_image(input_image)

            # Remove background
            output_image = remove(input_image)

            # Convert to white background
            white_bg = Image.new("RGB", output_image.size, (255, 255, 255))
            white_bg.paste(output_image, mask=output_image.split()[-1])

            # Save the image to a bytes buffer
            img_byte_arr = io.BytesIO()
            white_bg.save(img_byte_arr, format="PNG")
            img_byte_arr.seek(0)

            # Return the processed image
            return send_file(img_byte_arr, mimetype="image/png")

        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return {"status": "error", "message": str(e)}, 500

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
