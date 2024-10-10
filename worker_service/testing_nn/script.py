# install_dependencies.py
import subprocess
import sys

def install_requirements(file):
    """Install the packages listed in the requirements file."""
    try:
        with open(file, 'r') as f:
            packages = f.read().strip().split('\n')

        for package in packages:
            if package:  # Skip empty lines
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print("All packages installed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    install_requirements('requirements.txt')
