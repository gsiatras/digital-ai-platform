from minio import Minio
from minio.error import S3Error
import os
import io
import json

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

def download_model_from_minio(bucket_name, object_name):
    """Downloads a model from Minio and returns the data as a BytesIO stream."""
    try:
        # Get data of an object.
        response = minio_client.get_object(bucket_name, object_name)
        # Read the entire object data into a BytesIO object
        model_data = io.BytesIO(response.read())
        return model_data
    except S3Error as err:
        print(err)
        raise

    finally:
        if response:
            response.close()
            response.release_conn()

            

def download_image_from_minio(bucket_name, object_name):
    """Download an image file from a Minio bucket and return it as bytes."""
    try:
        found = minio_client.bucket_exists(bucket_name)
        if not found:
            raise ValueError(f"Bucket {bucket_name} does not exist")

        # Download the file from Minio
        image_data = minio_client.get_object(bucket_name, object_name)
        return image_data.read()  # Return the image data as bytes
    except S3Error as e:
        print(f"Minio S3 error: {e}")
        raise
    except Exception as e:
        print(f"Error while downloading image: {e}")
        raise


def upload_results_to_minio(bucket_name, object_name, results):
    """Upload prediction results to a Minio bucket. Create the bucket if it doesn't exist."""
    try:
        # Check if the bucket exists
        found = minio_client.bucket_exists(bucket_name)
        if not found:
            print(f"Bucket {bucket_name} does not exist. Creating it...")
            minio_client.make_bucket(bucket_name)
            print(f"Bucket {bucket_name} created successfully.")

        # Convert results to JSON format
        results_json = json.dumps(results)

        # Upload results as a JSON file
        minio_client.put_object(bucket_name, object_name, io.BytesIO(results_json.encode('utf-8')), len(results_json))
        print(f"Uploaded results to {bucket_name}/{object_name}")
    except S3Error as e:
        print(f"Minio S3 error: {e}")
        raise
    except Exception as e:
        print(f"Error while uploading results: {e}")
        raise


def upload_image_to_minio(bucket_name, object_name, image_data):
    """
    Upload an image to a MinIO bucket.
    :param bucket_name: Name of the MinIO bucket.
    :param object_name: Name of the object to store in the bucket.
    :param image_data: Binary image data.
    """
    try:
        found = minio_client.bucket_exists(bucket_name)
        if not found:
            minio_client.make_bucket(bucket_name)

        # Upload the image
        minio_client.put_object(bucket_name, object_name, io.BytesIO(image_data), len(image_data))
    except S3Error as e:
        raise
    except Exception as e:
        raise