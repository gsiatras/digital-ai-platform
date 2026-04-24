import os
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify
from minio_utils import model_exists_in_minio, check_file_existence, list_files_with_prefix
from db_utils import (
    create_job, complete_job, fail_job, get_avg_energy_per_worker,
    create_experiment, increment_experiment_progress, complete_experiment,
)
from kepler_utils import (
    get_container_cpu_time_ms, compute_energy_joules, compute_carbon_gco2,
    CARBON_INTENSITY_GCO2_KWH,
)
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

WORKER_PORT = 5000
WORKER_URLS = os.environ.get(
    "WORKER_URLS", "worker-a-service,worker-b-service,worker-c-service"
).split(",")

# Thread-safe round-robin index (shared between single jobs and experiments)
_rr_lock = threading.Lock()
_rr_index = 0


def _next_worker():
    global _rr_index
    with _rr_lock:
        host = WORKER_URLS[_rr_index % len(WORKER_URLS)]
        _rr_index += 1
    return host


# ── Core job execution ─────────────────────────────────────────────────────────

def _execute_job(job_id, input_file, worker_host, experiment_id=None):
    """
    Create DB record, call worker /predict, measure energy via Kepler,
    update DB with results. Returns dict with status and metrics.
    """
    try:
        create_job(job_id, input_file, worker_host, experiment_id=experiment_id)
    except Exception as e:
        logger.error(f"DB error creating job {job_id}: {e}")

    try:
        cpu_before = get_container_cpu_time_ms(worker_host)
        start = time.time()
        response = requests.post(
            f"http://{worker_host}:{WORKER_PORT}/predict",
            json={"job_id": job_id, "input_file": input_file},
        )
        latency_ms = (time.time() - start) * 1000
        cpu_after = get_container_cpu_time_ms(worker_host)

        energy_joules = None
        carbon_gco2 = None
        if cpu_before is not None and cpu_after is not None and cpu_after >= cpu_before:
            delta_ms = cpu_after - cpu_before
            energy_joules = compute_energy_joules(delta_ms)
            carbon_gco2 = compute_carbon_gco2(energy_joules, worker_host)

        if response.status_code == 200:
            body = response.json()
            detections_count = len(body.get("results", []))
            result_path = f"{job_id}_annotated_image.png"
            try:
                complete_job(job_id, latency_ms, result_path,
                             energy_joules, carbon_gco2, detections_count)
            except Exception as e:
                logger.error(f"DB error completing job {job_id}: {e}")
            logger.info(
                f"Job {job_id} done: worker={worker_host} latency={latency_ms:.0f}ms "
                f"detections={detections_count} energy={energy_joules}J"
            )
            return {"status": "completed", "job_id": job_id, "detections": detections_count}
        else:
            try:
                fail_job(job_id)
            except Exception as e:
                logger.error(f"DB error failing job {job_id}: {e}")
            logger.error(f"Worker error for job {job_id}: {response.text}")
            return {"status": "failed", "job_id": job_id}

    except Exception as e:
        try:
            fail_job(job_id)
        except Exception:
            pass
        logger.error(f"Exception running job {job_id}: {e}")
        return {"status": "failed", "job_id": job_id, "error": str(e)}


# ── Experiment runner (background) ─────────────────────────────────────────────

def _run_experiment(experiment_id, files):
    """Submit all files as jobs (2 concurrent streams), update experiment progress."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = {
            ex.submit(_execute_job, str(uuid.uuid4()), f, _next_worker(), experiment_id): f
            for f in files
        }
        for future in as_completed(futures):
            result = future.result()
            if result["status"] == "completed":
                try:
                    increment_experiment_progress(experiment_id, completed=1)
                except Exception as e:
                    logger.error(f"DB progress update error: {e}")
            else:
                try:
                    increment_experiment_progress(experiment_id, failed=1)
                except Exception as e:
                    logger.error(f"DB progress update error: {e}")
    try:
        complete_experiment(experiment_id)
    except Exception as e:
        logger.error(f"DB complete experiment error: {e}")
    logger.info(f"Experiment {experiment_id} finished.")


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/start_experiment", methods=["POST"])
def start_experiment():
    data = request.json or {}
    dataset = data.get("dataset")
    name = data.get("name") or f"{dataset}-exp"

    if not dataset:
        return jsonify({"error": "dataset required"}), 400

    files = list_files_with_prefix("input-files", f"{dataset}/")
    if not files:
        return jsonify({"error": f"No files found for dataset '{dataset}'"}), 404

    experiment_id = str(uuid.uuid4())
    try:
        create_experiment(experiment_id, name, dataset, total_jobs=len(files))
    except Exception as e:
        return jsonify({"error": f"DB error: {e}"}), 500

    threading.Thread(
        target=_run_experiment, args=(experiment_id, files), daemon=True
    ).start()

    return jsonify({"experiment_id": experiment_id, "total_jobs": len(files)}), 200


@app.route("/initialize_job", methods=["POST"])
def initialize_job():
    data = request.json or {}
    job_id = data.get("job_id")
    input_file = data.get("input_file")

    if not job_id or not input_file:
        return jsonify({"error": "Missing required fields (job_id, input_file)"}), 400
    if not check_file_existence(input_file):
        return jsonify({"error": f"File '{input_file}' not found in MinIO"}), 404

    worker_host = _next_worker()
    result = _execute_job(job_id, input_file, worker_host)

    if result["status"] == "completed":
        return jsonify({"message": "Job initialized successfully", "job_id": job_id}), 200
    return jsonify({"error": "Worker failed", "job_id": job_id}), 500


def _load_model_on_worker(worker_host, model_name):
    try:
        response = requests.post(
            f"http://{worker_host}:{WORKER_PORT}/load_model",
            json={"model_name": model_name},
            timeout=120,
        )
        return {"worker_id": worker_host, "status": response.json()}
    except Exception as e:
        return {"worker_id": worker_host, "error": str(e)}


@app.route("/load_model", methods=["POST"])
def load_model():
    model_id = request.json.get("model_id")
    if not model_id:
        return jsonify({"error": "No model_id provided"}), 400
    model_name = f"{model_id}.pt"
    if not model_exists_in_minio("models", model_name):
        return jsonify({"error": f"Model {model_name} not found in MinIO"}), 404

    with ThreadPoolExecutor(max_workers=len(WORKER_URLS)) as ex:
        futures = [ex.submit(_load_model_on_worker, w, model_name) for w in WORKER_URLS]
        results = [f.result() for f in futures]

    errors = [r for r in results if "error" in r]
    if errors:
        return jsonify({"warning": "Some workers failed", "results": results}), 207
    return jsonify({"message": f"Model {model_name} loaded on all workers", "results": results}), 200


def _query_worker(worker_host):
    try:
        response = requests.get(f"http://{worker_host}:{WORKER_PORT}/get_model", timeout=5)
        if response.status_code == 200:
            return {"worker_id": worker_host, "model_loaded": response.json().get("model_loaded")}
        return {"worker_id": worker_host, "error": response.json().get("error")}
    except Exception as e:
        return {"worker_id": worker_host, "error": str(e)}


@app.route("/list_models", methods=["GET"])
def list_models():
    with ThreadPoolExecutor(max_workers=len(WORKER_URLS)) as ex:
        futures = {ex.submit(_query_worker, w): w for w in WORKER_URLS}
        results = {f.result()["worker_id"]: f.result() for f in as_completed(futures)}

    try:
        avg_energy = get_avg_energy_per_worker()
    except Exception as e:
        logger.warning(f"Could not fetch avg energy from DB: {e}")
        avg_energy = {}

    for w in WORKER_URLS:
        results[w]["avg_energy_j"] = round(avg_energy[w], 3) if w in avg_energy else None
        results[w]["carbon_intensity"] = CARBON_INTENSITY_GCO2_KWH.get(w)

    return jsonify([results[w] for w in WORKER_URLS]), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
