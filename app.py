import os
from flask import Flask, request, render_template, send_file
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

            # Remove background using Remove.bg API
            output_image = remove_background(file.stream)

            # Convert to white background
            white_bg = Image.new("RGB", output_image.size, (255, 255, 255))
            white_bg.paste(output_image, mask=output_image.split()[-1])

            # Save the image to a bytes buffer
            img_byte_arr = io.BytesIO()
            white_bg.save(img_byte_arr, format="PNG")
            img_byte_arr.seek(0)

            # Clear memory
            del output_image, white_bg

            # Return the processed image
            return send_file(img_byte_arr, mimetype="image/png")

        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return {"status": "error", "message": str(e)}, 500

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
