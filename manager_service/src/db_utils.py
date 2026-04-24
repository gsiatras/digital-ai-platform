import os
import psycopg2
from psycopg2.extras import RealDictCursor

POSTGRES_URL = os.environ.get(
    "POSTGRES_URL",
    "postgresql://platform:platform1234@postgres-service:5432/platform"
)


def _connect():
    return psycopg2.connect(POSTGRES_URL)


# ── Experiments ────────────────────────────────────────────────────────────────

def create_experiment(experiment_id, name, dataset, algorithm="round-robin", total_jobs=0):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO experiments (id, name, dataset, algorithm, total_jobs)
                   VALUES (%s, %s, %s, %s, %s)""",
                (experiment_id, name, dataset, algorithm, total_jobs),
            )


def increment_experiment_progress(experiment_id, completed=0, failed=0):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE experiments
                   SET completed_jobs = completed_jobs + %s,
                       failed_jobs    = failed_jobs    + %s
                   WHERE id = %s""",
                (completed, failed, experiment_id),
            )


def complete_experiment(experiment_id):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE experiments
                   SET status = 'completed', completed_at = NOW()
                   WHERE id = %s""",
                (experiment_id,),
            )


# ── Jobs ───────────────────────────────────────────────────────────────────────

def create_job(job_id, input_file, worker_assigned, experiment_id=None):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO jobs (id, input_file, worker_assigned, status, experiment_id)
                   VALUES (%s, %s, %s, 'running', %s)""",
                (job_id, input_file, worker_assigned, experiment_id),
            )


def complete_job(job_id, latency_ms, result_path,
                 energy_joules=None, carbon_gco2=None, detections_count=None):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE jobs
                   SET status='completed', latency_ms=%s, result_path=%s,
                       energy_joules=%s, carbon_gco2=%s, detections_count=%s,
                       completed_at=NOW()
                   WHERE id=%s""",
                (latency_ms, result_path, energy_joules, carbon_gco2, detections_count, job_id),
            )


def fail_job(job_id):
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET status='failed', completed_at=NOW() WHERE id=%s",
                (job_id,),
            )


def get_avg_energy_per_worker():
    with _connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT worker_assigned, AVG(energy_joules) AS avg_energy_j
                   FROM jobs
                   WHERE status='completed' AND energy_joules IS NOT NULL
                   GROUP BY worker_assigned"""
            )
            return {row["worker_assigned"]: row["avg_energy_j"] for row in cur.fetchall()}
