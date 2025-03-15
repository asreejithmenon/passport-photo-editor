import os
from flask import Flask, request, render_template, send_file
from rembg import remove
from PIL import Image
import io

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" not in request.files:
            return "No file uploaded", 400
        file = request.files["file"]
        if file.filename == "":
            return "No file selected", 400

        # Process the image
        input_image = Image.open(file.stream)
        output_image = remove(input_image)

        # Convert to white background
        white_bg = Image.new("RGB", output_image.size, (255, 255, 255))
        white_bg.paste(output_image, mask=output_image.split()[-1])

        # Save the image to a bytes buffer
        img_byte_arr = io.BytesIO()
        white_bg.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)

        # Return the processed image as a response
        return send_file(
            img_byte_arr,
            mimetype="image/png",
            as_attachment=False,  # Set to False to display the image in the browser
        )

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
