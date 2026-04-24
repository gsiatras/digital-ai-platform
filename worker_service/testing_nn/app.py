import os
import io
import logging
from flask import Flask, request, jsonify
from utils import load_model, predict_and_detect, draw_boxes_on_image
from minio_utils import download_model_from_minio, download_image_from_minio, upload_results_to_minio, upload_image_to_minio
import time
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Minio configuration
MODEL_BUCKET = "models"
IMAGE_BUCKET = "input-files"
RESULTS_BUCKET = "result-files"
MODEL_NAME = os.getenv("MODEL_NAME", "yolov10n.pt")

# Global variable to track model loading status and the model
model = None
model_name_loaded = None
model_loading = False
model_lock = threading.Lock()


def _do_load_model(model_name):
    """Load a specific model file from MinIO into memory. Caller must hold model_lock."""
    global model, model_name_loaded, model_loading
    model_loading = True
    try:
        logger.info(f"Downloading {model_name} from MinIO.")
        model_data = download_model_from_minio(MODEL_BUCKET, model_name)
        logger.info("Loading model into memory.")
        model = load_model(model_data)
        model_name_loaded = model_name
        logger.info(f"Model {model_name} loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        model = None
        model_name_loaded = None
    finally:
        model_loading = False


def load_the_model():
    """Load the default MODEL_NAME if not already loaded."""
    global model, model_loading
    with model_lock:
        if model is not None or model_loading:
            return
        _do_load_model(MODEL_NAME)


# Initial model loading attempt
logger.info("Attempting initial model load.")
load_the_model()


@app.route('/status', methods=['GET'])
def status():
    logger.info("Received request at /status endpoint.")
    if model is None:
        logger.error("Model is not loaded.")
        return jsonify({"error": "Model not loaded"}), 500
    logger.info("Model is ready.")
    return jsonify({"message": f"Model {MODEL_NAME} is ready"}), 200


@app.route('/get_model', methods=['GET'])
def get_model():
    global model
    logger.info("Received request at /get_model endpoint.")
    if model is None:
        logger.info("Model is not loaded. Attempting to reload.")
        load_the_model()  # Call the model loading function

        if model is None:
            logger.error("Failed to load model.")
            return jsonify({"error": "Model not loaded"}), 500  # Return error if still not loaded
        else:
            logger.info("Model reloaded successfully.")
            return jsonify({"message": "Model reloaded successfully", "model_loaded": model_name_loaded}), 200

    logger.info("Model is already loaded.")
    return jsonify({"model_loaded": model_name_loaded}), 200


@app.route('/load_model', methods=['POST'])
def load_model_endpoint():
    """Load a specific model by name from MinIO, replacing any currently loaded model."""
    global model, model_name_loaded, model_loading
    model_name = request.json.get('model_name') if request.json else None
    if not model_name:
        return jsonify({"error": "model_name required"}), 400

    with model_lock:
        if model_loading:
            return jsonify({"error": "Model loading already in progress"}), 409
        model = None
        model_name_loaded = None
        _do_load_model(model_name)

    if model is None:
        return jsonify({"error": f"Failed to load model {model_name}"}), 500
    return jsonify({"message": f"Model {model_name} loaded", "model_loaded": model_name}), 200


@app.route('/predict', methods=['POST'])
def predict():
    logger.info("Received request at /predict endpoint.")
    if model is None:
        logger.error("Model is not loaded.")
        return jsonify({"error": "Model not loaded"}), 500


    image_name = request.json['input_file']
    job_id = request.json['job_id']
    logger.info(f"Processing image: {image_name} for job ID: {job_id}")

    # Download the image from the input-files bucket
    try:
        logger.info(f"Downloading image {image_name} from MinIO.")
        image_data = download_image_from_minio(IMAGE_BUCKET, image_name)
        logger.info("Image downloaded successfully.")

        # Perform prediction
        logger.info("Starting prediction.")
        boxes = predict_and_detect(image_data, model)
        logger.info("Prediction completed successfully.")

        # Upload the results to the results bucket
        results_file_name = f"{job_id}_results.json"
        logger.info(f"Uploading results to MinIO as {results_file_name}.")
        upload_results_to_minio(RESULTS_BUCKET, results_file_name, boxes)
        logger.info("Results uploaded successfully.")

        # Draw bounding boxes on the image
        logger.info("Drawing bounding boxes on the image.")
        logging.info(boxes)
        annotated_image = draw_boxes_on_image(image_data, boxes)
        logger.info("Bounding boxes drawn successfully.")

        # Upload the annotated image to the results bucket
        annotated_image_name = f"{job_id}_annotated_image.png"
        logger.info(f"Uploading annotated image to MinIO as {annotated_image_name}.")
        upload_image_to_minio(RESULTS_BUCKET, annotated_image_name, annotated_image)
        logger.info("Annotated image uploaded successfully.")

        return jsonify({"message": "Prediction successful", "results": boxes}), 200
    except Exception as e:
        logger.error(f"Failed to process the image: {str(e)}")
        return jsonify({"error": f"Failed to process the image: {str(e)}"}), 500


if __name__ == "__main__":
    logger.info("Starting Flask application.")
    app.run(host='0.0.0.0', port=5000)