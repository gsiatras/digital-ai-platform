import os
from flask import Flask, request, jsonify
from utils import load_model, predict_and_detect
from minio_utils import download_model_from_minio

app = Flask(__name__)

# Minio configuration
MINIO_BUCKET = "models"
MODEL_NAME = os.getenv("MODEL_NAME", "yolov10n.pt")
TEMP_MODEL_PATH = f"/tmp/{MODEL_NAME}"

# Download the model from Minio to the local temp path
try:
    download_model_from_minio(MINIO_BUCKET, MODEL_NAME, TEMP_MODEL_PATH)
    print(f"Model {MODEL_NAME} downloaded successfully from Minio.")
except Exception as e:
    print(f"An error occurred while downloading the model: {e}")

# Load the model once downloaded
model = None
try:
    model = load_model(TEMP_MODEL_PATH)
    print("Model loaded successfully.")
except FileNotFoundError as e:
    print(f"Error loading model: {e}")
except Exception as e:
    print(f"An error occurred while loading the model: {e}")

@app.route('/predict', methods=['POST'])
def predict():
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500

    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image_file = request.files['image']
    image_path = os.path.join("/tmp", image_file.filename)
    image_file.save(image_path)

    try:
        boxes = predict_and_detect(image_path, model)
        return jsonify(boxes)
    finally:
        os.remove(image_path)  # Clean up the saved image after prediction

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
