import os
import subprocess
from flask import Flask, request, jsonify
from minio_utils import model_exists_in_minio, check_file_existence
import requests
from kubernetes import client, config
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# Kubernetes worker service details
WORKER_SERVICE_NAME = "worker-service"
WORKER_NAMESPACE = "platform"
WORKER_PORT = 5000

@app.route('/load_model', methods=['POST'])
def load_model():
    model_id = request.json.get('model_id')
    if not model_id:
        return jsonify({"error": "No model_id provided"}), 400

    # Check if model exists in MinIO
    if not model_exists_in_minio("models", f"{model_id}.pt"):
        return jsonify({"error": f"Model {model_id} not found in MinIO"}), 404

    # Create a Kubernetes Job
    job_name = f"load-model-{model_id}"
    try:
        job_yaml = f"""
          apiVersion: batch/v1
          kind: Job
          metadata:
            name: {job_name}
          spec:
            template:
              spec:
                containers:
                - name: model-loader
                  image: gsiatras13/digital_platform-worker_service:a1.1
                  env:
                  - name: MODEL_NAME
                    value: "{model_id}.pt"
                  - name: MODEL_BUCKET
                    value: "models"
                  - name: IMAGE_BUCKET
                    value: "input-files"
                  - name: RESULTS_BUCKET
                    value: "result-files"
                restartPolicy: Never
            backoffLimit: 2
        """
        with open(f"/tmp/{job_name}.yaml", "w") as f:
            f.write(job_yaml)
        subprocess.run(["kubectl", "apply", "-f", f"/tmp/{job_name}.yaml"], check=True)
        return jsonify({"message": f"Model {model_id} loading job created successfully", "job_name": job_name}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to create Kubernetes Job: {str(e)}"}), 500



@app.route('/list_models', methods=['GET'])
def list_models():
    try:
        # Load Kubernetes config (works inside the cluster)
        config.load_incluster_config()
        v1 = client.CoreV1Api()

        # Get worker pods
        worker_pods = v1.list_namespaced_pod(namespace=WORKER_NAMESPACE, label_selector="app=worker-service")

        models_info = []
        for pod in worker_pods.items:
            pod_name = pod.metadata.name
            worker_url = f"http://{pod_name}.{WORKER_SERVICE_NAME}.{WORKER_NAMESPACE}.svc.cluster.local:{WORKER_PORT}/get_model"
            try:
                response = requests.get(worker_url)
                if response.status_code == 200:
                    models_info.append({
                        "worker_id": pod_name,
                        "model_loaded": response.json().get("model_loaded")
                    })
                else:
                    models_info.append({
                        "worker_id": pod_name,
                        "error": response.json().get("error")
                    })
            except Exception as e:
                models_info.append({
                    "worker_id": pod_name,
                    "error": str(e)
                })

        return jsonify(models_info), 200
    except Exception as e:
        return jsonify({"error": f"Failed to list models: {str(e)}"}), 500
    

@app.route('/initialize_job', methods=['POST'])
def initialize_job():
    data = request.json
    job_id = data.get('job_id')
    input_file = data.get('input_file')

    # Validate required fields
    if not job_id or not input_file:
        return jsonify({"error": "Missing required fields (job_id, input_file)"}), 400

    # Check if the input file exists in the MinIO bucket
    if not check_file_existence(input_file):
        return jsonify({"error": f"File '{input_file}' not found in MinIO bucket 'input-files'"}), 404

    try:
        # Prepare the payload for the worker service
        payload = {
            'job_id': job_id,
            'input_file': input_file
        }
        headers = {
            'Content-Type': 'application/json',
        }

        # Send the job to the worker service
        worker_service_url = f"http://{WORKER_SERVICE_NAME}.{WORKER_NAMESPACE}.svc.cluster.local:{WORKER_PORT}/predict"
        response = requests.post(worker_service_url, json=payload, headers=headers)

        # Check the response from the worker service
        if response.status_code == 200:
            return jsonify({"message": "Job initialized successfully", "job_id": job_id}), 200
        else:
            logging.error(f"Failed to initialize job with worker service: {response.text}")
            return jsonify({"error": f"Failed to initialize job with worker service: {response.text}"}), response.status_code

    except Exception as e:
        logging.error(f"Error while initializing job: {e}")
        return jsonify({"error": f"Error while initializing job: {str(e)}", "job_id": job_id}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050)