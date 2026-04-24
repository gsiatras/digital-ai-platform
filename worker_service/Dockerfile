FROM python:3.9-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./testing_nn/requirements.txt .

# CPU-only torch (~200MB vs ~2GB for CUDA). No GPU in minikube.
RUN pip install --upgrade pip && \
    pip install torch==2.4.1+cpu torchvision==0.19.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r requirements.txt && \
    pip install --no-deps ultralytics==8.3.73

COPY testing_nn/ ./testing_nn/

CMD ["python", "testing_nn/app.py"]
