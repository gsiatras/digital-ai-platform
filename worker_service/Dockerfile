FROM python:3.9-slim

# Install dependencies including OpenGL libraries
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY ./testing_nn/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install --no-deps ultralytics

# Copy application code
COPY testing_nn/ ./testing_nn/

# Command to run your application
CMD ["python", "testing_nn/app.py"]