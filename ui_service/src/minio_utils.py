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

def create_minio_bucket():
    # Ensure both 'input-files' and 'models' buckets exist
    for bucket in [MINIO_BUCKET, MINIO_MODELS_BUCKET]:
        found = minio_client.bucket_exists(bucket)
        if not found:
            minio_client.make_bucket(bucket)
            print(f"Created bucket: {bucket}")
    print('Buckets exist')

def check_file_existence(filename):
    try:
        minio_client.stat_object(MINIO_BUCKET, filename)
        return True
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return False
        else:
            raise


def upload_file_to_minio(file, file_id, bucket_name):
    file_data = file.read()  # Read file data once
    file_size = len(file_data)  # Get file size
    file.seek(0)  # Reset pointer to the beginning of the file

    # Upload file to Minio
    minio_client.put_object(
        bucket_name,
        file_id,
        BytesIO(file_data),  # Use BytesIO to provide file data as a stream
        file_size,           # Provide the file size
        content_type=file.content_type  # Set content type, e.g., application/octet-stream for .pt files
    )

