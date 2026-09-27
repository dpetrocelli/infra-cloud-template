FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY blockchain.py node.py .

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8090
ENV DATA_DIR=/data PORT=8090 DIFFICULTY=4 PEERS=""

CMD ["python", "node.py"]
