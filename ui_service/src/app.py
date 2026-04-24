from flask import Flask, request, jsonify, send_file, render_template
import logging
import uuid
import requests
import os
import io
from minio_utils import create_minio_bucket, check_file_existence, upload_file_to_minio, list_files_in_bucket, download_file_from_minio
from db_utils import get_jobs

app = Flask(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_SERVICE_URL", "minio-service:9000")
MINIO_BUCKET = "input-files"
MINIO_MODELS_BUCKET = "models"
WORKER_SERVICE = os.getenv("WORKER_SERVICE_URL", "http://worker-service:5000")
MANAGER_SERVICE = os.getenv("MANAGER_SERVICE_URL", "http://manager-service:5050")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/nodes/status', methods=['GET'])
def nodes_status():
    try:
        resp = requests.get(f"{MANAGER_SERVICE}/list_models", timeout=15)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs', methods=['GET'])
def api_jobs():
    try:
        jobs = get_jobs()
        result = []
        for j in jobs:
            result.append({
                "id": str(j["id"]),
                "input_file": j["input_file"] or "—",
                "worker": j["worker_assigned"] or "—",
                "latency": round(j["latency_ms"], 1) if j["latency_ms"] is not None else "—",
                "energy": j["energy_joules"] if j["energy_joules"] is not None else "—",
                "carbon": j["carbon_gco2"] if j["carbon_gco2"] is not None else "—",
                "status": j["status"],
            })
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Failed to fetch jobs from DB: {e}")
        return jsonify([]), 200


@app.route('/api/files', methods=['GET'])
def api_files():
    try:
        files = list_files_in_bucket('input-files')
        return jsonify(files), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/result_image', methods=['GET'])
def result_image():
    file_name = request.args.get('file_name')
    if not file_name:
        return jsonify({"error": "file_name required"}), 400
    try:
        file_data = download_file_from_minio("result-files", file_name)
        return send_file(io.BytesIO(file_data), mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@app.route('/jobs/submit', methods=['POST'])
def submit_job():
    data = request.json
    input_file = data.get('input_file')

    if not input_file:
        return jsonify({"error": "Missing required fields (input_file)"}), 400

    job_id = str(uuid.uuid4())

    try:
        payload = {'job_id': job_id, 'input_file': input_file}
        response = requests.post(
            f"{MANAGER_SERVICE}/initialize_job",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            return jsonify({"message": "Job submitted successfully", "job_id": job_id}), 200
        else:
            logger.error(f"Failed to submit job: {response.text}")
            return jsonify({"error": f"Failed to submit job: {response.text}"}), response.status_code

    except Exception as e:
        logger.error(f"Error while submitting job: {e}")
        return jsonify({"error": f"Error while submitting job: {str(e)}", "job_id": job_id}), 500


@app.route('/minio/health/live', methods=['GET'])
def check_minio_health():
    try:
        response = requests.get(f"http://{MINIO_ENDPOINT}/minio/health/live")
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
        upload_file_to_minio(file, file.filename, MINIO_BUCKET)
        return jsonify({"message": "File uploaded successfully", "file_id": file.filename}), 200
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        return jsonify({"error": f"Failed to upload file: {str(e)}"}), 500


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
        upload_file_to_minio(file, file.filename, MINIO_MODELS_BUCKET)
        return jsonify({"message": "Model uploaded successfully", "file_id": file.filename}), 200
    except Exception as e:
        logger.error(f"Failed to upload model: {e}")
        return jsonify({"error": f"Failed to upload model: {str(e)}"}), 500


@app.route('/load_model', methods=['POST'])
def load_model():
    model_id = request.json.get('model_id')
    if not model_id:
        return jsonify({"error": "No model_id provided"}), 400

    try:
        response = requests.post(f"{MANAGER_SERVICE}/load_model", json={"model_id": model_id})
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
        return jsonify({"error": f"Failed to list files: {str(e)}"}), 500


@app.route('/list_models', methods=['GET'])
def list_models():
    try:
        response = requests.get(f"{MANAGER_SERVICE}/list_models")
        return response.json(), response.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to list models: {str(e)}"}), 500


@app.route('/get_result_file', methods=['GET'])
def get_result_file():
    file_name = request.args.get('file_name')
    if not file_name:
        return jsonify({"error": "file_name query parameter is required"}), 400

    try:
        if not check_file_existence(file_name, "result-files"):
            return jsonify({"error": f"File '{file_name}' not found in result-files bucket"}), 404

        file_data = download_file_from_minio("result-files", file_name)
        return send_file(io.BytesIO(file_data), as_attachment=True, download_name=file_name)
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve file: {str(e)}"}), 500


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


if __name__ == '__main__':
    create_minio_bucket()
    app.run(host='0.0.0.0', port=8080, debug=True)
