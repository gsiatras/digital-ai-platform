from minio import Minio
from minio.error import S3Error
import os
from io import BytesIO
import logging

MINIO_ENDPOINT = os.getenv("MINIO_SERVICE_URL", "minio-service:9000")
MINIO_ACCESS_KEY = 'platform'
MINIO_SECRET_KEY = 'platform1234'
MINIO_BUCKET = 'input-files'
MINIO_MODELS_BUCKET = 'models'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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


def check_file_existence(filename, bucket_name=None):
    """
    Check if a file exists in a MinIO bucket.

    :param filename: Name of the file to check.
    :param bucket_name: Name of the MinIO bucket. Defaults to MINIO_BUCKET if not provided.
    :return: True if the file exists, False otherwise.
    """
    if bucket_name is None:
        bucket_name = MINIO_BUCKET  # Use the default bucket if not provided

    try:
        logger.info(bucket_name)
        minio_client.stat_object(bucket_name, filename)
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

def list_files_in_bucket(bucket_name):
    try:
        files = [obj.object_name for obj in minio_client.list_objects(bucket_name)]
        return files
    except S3Error as e:
        raise Exception(f"Error listing files in bucket: {e}")
    

def download_file_from_minio(bucket_name, file_name):
    """
    Download a file from a MinIO bucket and return its binary data.
    
    :param bucket_name: Name of the MinIO bucket.
    :param file_name: Name of the file to download.
    :return: Binary data of the file.
    """
    try:
        # Get the object from MinIO
        response = minio_client.get_object(bucket_name, file_name)
        # Read the file data
        file_data = response.read()
        return file_data
    except S3Error as e:
        raise Exception(f"Failed to download file '{file_name}' from bucket '{bucket_name}': {e}")
    finally:
        # Ensure the response is closed to release resources
        if 'response' in locals():
            response.close()
            response.release_conn()