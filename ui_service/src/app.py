from flask import Flask, request, jsonify, send_file
import logging
import uuid
import requests
import os
import io
from minio_utils import create_minio_bucket, check_file_existence, upload_file_to_minio, list_files_in_bucket, download_file_from_minio

app = Flask(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_SERVICE_URL", "minio-service:9000")
MINIO_BUCKET = "input-files"
MINIO_MODELS_BUCKET = "models"
WORKER_SERVICE = os.getenv("WORKER_SERVICE_URL", "worker-service:5000")
MANAGER_SERVICE = os.getenv("MANAGER_SERVICE_URL", "manager-service:5050")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@app.route('/jobs/submit', methods=['POST'])
def submit_job():
    data = request.json
    input_file = data.get('input_file')

    if not input_file:
        return jsonify({"error": "Missing required fields (input_file)"}), 400

    job_id = str(uuid.uuid4())  # Generate a unique job ID

    try:
        # Prepare the payload for the manager service
        payload = {
            'job_id': job_id,
            'input_file': input_file
        }
        headers = {
            'Content-Type': 'application/json',
        }

        # Send the job to the manager service
        manager_service_url = f"{MANAGER_SERVICE}/initialize_job"
        response = requests.post(manager_service_url, json=payload, headers=headers)

        # Check the response from the manager service
        if response.status_code == 200:
            return jsonify({"message": "Job submitted successfully", "job_id": job_id}), 200
        else:
            logging.error(f"Failed to submit job to manager service: {response.text}")
            return jsonify({"error": f"Failed to submit job to manager service: {response.text}"}), response.status_code

    except Exception as e:
        logging.error(f"Error while submitting job: {e}")
        return jsonify({"error": f"Error while submitting job: {str(e)}", "job_id": job_id, "input_file": input_file}), 500


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
        file_id = file.filename
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
        file_id = file.filename
        upload_file_to_minio(file, file_id, MINIO_MODELS_BUCKET)
        return jsonify({"message": "Model uploaded successfully", "file_id": file_id}), 200
    except Exception as e:
        logging.error(f"Failed to upload model to Minio: {e}")
        return jsonify({"error": f"Failed to upload model to Minio: {str(e)}"}), 500
    

@app.route('/load_model', methods=['POST'])
def load_model():
    model_id = request.json.get('model_id')
    if not model_id:
        return jsonify({"error": "No model_id provided"}), 400

    try:
        manager_service_url = f"{MANAGER_SERVICE}/load_model"  
        response = requests.post(manager_service_url, json={"model_id": model_id})
        return response.json(), response.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to communicate with Manager service: {str(e)}"}), 500


@app.route('/list_files', methods=['GET'])
def list_files():
    bucket_name = request.args.get('bucket_name')
    
    if not bucket_name:
        return jsonify({"error": "Bucket name is required"}), 400
    
    try:
        files = list_files_in_bucket(bucket_name)
        return jsonify({"bucket": bucket_name, "files": files}), 200
    except Exception as e:
        logging.error(f"Failed to list files in bucket '{bucket_name}': {e}")
        return jsonify({"error": f"Failed to list files in bucket '{bucket_name}': {str(e)}"}), 500



@app.route('/list_models', methods=['GET'])
def list_models():
    try:
        manager_service_url = f"{MANAGER_SERVICE}/list_models"  
        response = requests.get(manager_service_url)
        return response.json(), response.status_code
    except Exception as e:
        logging.error(f"Failed to list models': {e}")
        return jsonify({"error": f"Failed to list models: {str(e)}"}), 500


@app.route('/routes', methods=['GET'])
def list_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "endpoint": rule.endpoint,
            "methods": list(rule.methods - {'HEAD', 'OPTIONS'}),
            "path": str(rule)
        })
    return jsonify(routes)


@app.route('/get_result_file', methods=['GET'])
def get_result_file():
    file_name = request.args.get('file_name')
    if not file_name:
        return jsonify({"error": "file_name query parameter is required"}), 400

    try:
        # Check if the file exists in the result-files bucket
        if not check_file_existence(file_name, "result-files"):
            return jsonify({"error": f"File '{file_name}' not found in result-files bucket"}), 404

        logger.info("DOwnload")
        # Download the file from MinIO
        file_data = download_file_from_minio("result-files", file_name)

        # Return the file as a downloadable response
        return send_file(
            io.BytesIO(file_data),
            as_attachment=True,
            download_name=file_name
        )
    except Exception as e:
        logging.error(f"Failed to retrieve file '{file_name}' from result-files bucket: {e}")
        return jsonify({"error": f"Failed to retrieve file '{file_name}' from result-files bucket: {str(e)}"}), 500
    


if __name__ == '__main__':
    create_minio_bucket()  # This can be expanded to ensure 'models' bucket is created as well
    app.run(host='0.0.0.0', port=8080, debug=True)
