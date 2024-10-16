import click
import requests
import os

"""
    User interface 
"""

SERVICE_URL = "http://localhost:8080"
token_file = "token.txt"


# Jobs command group
@click.group()
def jobs():
    """Manage jobs."""
    pass


@jobs.command()
@click.argument('input_name', type=str)
def submit(input_name):
    """Submit a new job."""
    # Prepare payload
    payload = {
        "input_file": input_name  # Assuming input_name is the name of the file to be submitted
    }

    # Make HTTP POST request to submit job
    headers = {"Content-Type": "application/json"}
    response = requests.post(f"{SERVICE_URL}/jobs/submit", json=payload, headers=headers)

    if response.status_code == 200:
        click.echo("Job submitted successfully.")
        click.echo(response.json())
    else:
        click.echo(f"Failed to submit job. Status code: {response.status_code}")
        click.echo(response.text)


@jobs.command()
@click.argument('job_id')
def status(job_id):
    """View the status of an existing job."""
    try:
        response = requests.get(f"{SERVICE_URL}/jobs/status/{job_id}")
        if response.status_code == 200:
            job_status = response.json()
            sub_status = job_status.get('sub_status', 'N/A')
            number_of_chunks = job_status.get('number_of_chunks', 'N/A')
            click.echo(f"Job ID: {job_status['job_id']}, Status: {job_status['status']}, Substatus: {sub_status}/{number_of_chunks}")
        elif response.status_code == 404:
            click.echo("Job not found.")
        else:
            click.echo(f"Failed to get job status. Status code: {response.status_code}")
            click.echo(response.text)
    except requests.RequestException as e:
        click.echo(f"Failed to connect to server: {e}")


@jobs.group()
def upload():
    """Upload files to Minio."""
    pass


@upload.command('input-file')
@click.argument('file_path', type=click.Path(exists=True))
def upload_input_file(file_path):
    """Upload an input file to Minio."""
    try:
        # Prepare file data for uploading
        file_name = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f)}

            response = requests.post(f"{SERVICE_URL}/upload", files=files)

            if response.status_code == 200:
                click.echo("Input file uploaded successfully.")
                click.echo(response.json())
            else:
                click.echo(f"Failed to upload input file. Status code: {response.status_code}")
                click.echo(response.text)
    except Exception as e:
        click.echo(f"Failed to upload input file: {e}")


@upload.command('model')
@click.argument('file_path', type=click.Path(exists=True))
def upload_model(file_path):
    """Upload a model file to Minio (models bucket)."""
    if not file_path.endswith('.pt'):
        click.echo("Error: Only .pt files are allowed for model uploads.")
        return

    try:
        # Prepare file data for uploading
        file_name = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            files = {'file': (file_name, f)}

            response = requests.post(f"{SERVICE_URL}/upload_model", files=files)

            if response.status_code == 200:
                click.echo("Model file uploaded successfully.")
                click.echo(response.json())
            else:
                click.echo(f"Failed to upload model file. Status code: {response.status_code}")
                click.echo(response.text)
    except Exception as e:
        click.echo(f"Failed to upload model file: {e}")


# Define the main CLI group
@click.group()
def cli():
    """Main CLI for job and admin management."""
    pass

# Add the command groups to the main CLI group
cli.add_command(jobs)

if __name__ == '__main__':
    cli()
