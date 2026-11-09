FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
# CPU-only PyTorch keeps the image small; this is a simulation, not GPU training.
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
# Code only. Bank data is NEVER baked into the image; it is mounted per bank at runtime.
COPY fraud_ai ./fraud_ai
COPY configs ./configs
