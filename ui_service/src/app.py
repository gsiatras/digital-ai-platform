from flask import Flask, request, jsonify
import logging
import uuid
import requests
import os
from minio_utils import create_minio_bucket, check_file_existence, upload_file_to_minio

app = Flask(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_SERVICE_URL", "minio-service:9000")
MINIO_BUCKET = "input-files"
MINIO_MODELS_BUCKET = "models"


@app.route('/jobs/submit', methods=['POST'])
def submit_job():
    data = request.json
    input_file = data.get('input_file')

    if not input_file:
        return jsonify({"error": "Missing required fields (input_file)"}), 400

    if input_file and not check_file_existence(input_file):
        return jsonify({"error": f"File '{input_file}' not found in Minio bucket"}), 404

    job_id = uuid.uuid4()

    try:
        # Send request to the manager service
        payload = {
            'job_id': str(job_id),
            'input_file': input_file
        }
        headers = {
            'Content-Type': 'application/json',
        }

        # Placeholder for forwarding job to the manager service
        return jsonify({"message": "Job submitted successfully and forwarded to manager service", "job_id": str(job_id)}), 200
    except Exception as e:
        logging.error(f"Failed to submit job to Cassandra: {e}")
        return jsonify({"error": f"Failed to submit job to Cassandra: {str(e)}", "job_id": str(job_id), "input_file": input_file}), 500


@app.route('/minio/health/live', methods=['GET'])
def check_minio_health():
    try:
        response = requests.get(f"{MINIO_ENDPOINT}/minio/health/live")
        response.raise_for_status()
        return jsonify({"status": "MinIO is healthy"})
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to connect to MinIO: {e}"}), 500


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Upload file to Minio bucket
        file_id = str(uuid.uuid4()) + "_" + file.filename
        upload_file_to_minio(file, file_id, MINIO_BUCKET)
        return jsonify({"message": "File uploaded successfully", "file_id": file_id}), 200
    except Exception as e:
        logging.error(f"Failed to upload file to Minio: {e}")
        return jsonify({"error": f"Failed to upload file to Minio: {str(e)}"}), 500


@app.route('/upload_model', methods=['POST'])
def upload_model():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.endswith(".pt"):
        return jsonify({"error": "Only .pt model files are allowed"}), 400

    try:
        # Upload .pt model file to the 'models' bucket
        file_id = str(uuid.uuid4()) + "_" + file.filename
        upload_file_to_minio(file, file_id, MINIO_MODELS_BUCKET)
        return jsonify({"message": "Model uploaded successfully", "file_id": file_id}), 200
    except Exception as e:
        logging.error(f"Failed to upload model to Minio: {e}")
        return jsonify({"error": f"Failed to upload model to Minio: {str(e)}"}), 500


if __name__ == '__main__':
    create_minio_bucket()  # This can be expanded to ensure 'models' bucket is created as well
    app.run(host='0.0.0.0', port=8080, debug=True)
