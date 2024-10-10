from flask import Flask, request, jsonify
import logging
import uuid
import requests
import os
from minio_utils import create_minio_bucket, check_file_existence

app = Flask(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_SERVICE_URL", "minio-service:9000")
# MANAGER_SERVICE_URL = os.getenv("MANAGER_SERVICE_URL", "http://manager-service.dena:8081")



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

        # response = requests.post(f'{MANAGER_SERVICE_URL}/initialize_job', json=payload, headers=headers)

        # if response.status_code == 200:
        #     return jsonify({"message": "Job submitted successfully and forwarded to manager service", "job_id": str(job_id)}), 200
        # else:
        #     logging.error(f"Failed to forward job to manager service: {response.status_code}, {response.text}")
        #     return jsonify({"error": f"Failed to forward job to manager service: {response.text}"}), response.status_code
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

if __name__ == '__main__':
    create_minio_bucket()
    app.run(host='0.0.0.0', port=8080, debug=True)