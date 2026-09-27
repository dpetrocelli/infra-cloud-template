# Minimal, student-readable image for the servicio patron.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# /data is where the persistent disk / PVC gets mounted in every class.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8080
ENV DATA_DIR=/data PORT=8080

CMD ["python", "main.py"]
