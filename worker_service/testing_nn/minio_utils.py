from minio import Minio
from minio.error import S3Error
import os

MINIO_ENDPOINT = os.getenv("MINIO_SERVICE_URL", "minio-service:9000")
MINIO_ACCESS_KEY = 'platform'
MINIO_SECRET_KEY = 'platform1234'

# Initialize the Minio client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False  # Set to True if you're using HTTPS
)

def download_model_from_minio(bucket_name, object_name, dest_path):
    """Download a model file from a Minio bucket."""
    try:
        found = minio_client.bucket_exists(bucket_name)
        if not found:
            raise ValueError(f"Bucket {bucket_name} does not exist")

        # Download the file from Minio
        minio_client.fget_object(bucket_name, object_name, dest_path)
        print(f"Downloaded {object_name} to {dest_path}")
    except S3Error as e:
        print(f"Minio S3 error: {e}")
        raise
    except Exception as e:
        print(f"Error while downloading model: {e}")
        raise
