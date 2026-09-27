# The model is trained ONCE, at build time, and baked into the image.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY train.py serve.py .
RUN python train.py

EXPOSE 8081
ENV MODEL_PATH=/app/model.joblib PORT=8081

CMD ["python", "serve.py"]
