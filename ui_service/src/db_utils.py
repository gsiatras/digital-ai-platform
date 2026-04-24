import os
import psycopg2
from psycopg2.extras import RealDictCursor

POSTGRES_URL = os.environ.get(
    "POSTGRES_URL",
    "postgresql://platform:platform1234@postgres-service:5432/platform"
)


def _connect():
    return psycopg2.connect(POSTGRES_URL)


def get_jobs(limit=100):
    with _connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]
