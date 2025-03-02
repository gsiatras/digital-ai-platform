from minio import Minio
from minio.error import S3Error
import os
from io import BytesIO

MINIO_ENDPOINT = os.getenv("MINIO_SERVICE_URL", "minio-service:9000")
MINIO_ACCESS_KEY = 'platform'
MINIO_SECRET_KEY = 'platform1234'
MINIO_BUCKET = 'input-files'
MINIO_MODELS_BUCKET = 'models'

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # Set to True if using HTTPS
)


def model_exists_in_minio(bucket_name, model_name):
    try:
        minio_client.stat_object(bucket_name, model_name)
        return True
    except Exception:
        return False
    

def check_file_existence(filename):
    try:
        minio_client.stat_object(MINIO_BUCKET, filename)
        return True
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return False
        else:
            raise