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


# Admin command group
@click.group()
def admin():
    """Administer the system."""
    pass



# Define the main CLI group
@click.group()
def cli():
    """Main CLI for job and admin management."""
    pass

# Add the command groups to the main CLI group
cli.add_command(jobs)
cli.add_command(admin)

if __name__ == '__main__':
    cli()