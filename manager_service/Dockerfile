FROM python:3.11.2 as build

ENV AUTH_SERVICE_URL="http://auth-service:8000"
ENV MINIO_SERVICE_URL='minio-service:9000'

WORKDIR /manager_service


COPY . .


RUN pip install --no-cache-dir -r src/requirements.txt

EXPOSE 8080

ENTRYPOINT [ "python", "src/app.py" ]
