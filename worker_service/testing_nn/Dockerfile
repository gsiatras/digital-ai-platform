FROM python:3.9-slim

# Install dependencies including OpenGL libraries
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install --no-deps ultralytics

# Copy the application code
COPY . .

# Set the environment variable for the model path (optional, can be overwritten at runtime)
ENV MODEL_PATH=/app/models/yolov10n.pt

# Command to run your application
CMD ["python", "app.py"]
