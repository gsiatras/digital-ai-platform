import os
from flask import Flask, request, jsonify
from utils import load_model, predict_and_detect

app = Flask(__name__)

# Load the model when the application starts
model_path = os.getenv("MODEL_PATH", r"D:\Diplomatiki\test\models\yolov10n.pt")

# Initialize the model variable
model = None

try:
    model = load_model(model_path)
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

    boxes = predict_and_detect(image_path, model)
    os.remove(image_path)  # Clean up the saved image

    return jsonify(boxes)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)