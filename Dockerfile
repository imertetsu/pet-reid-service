FROM python:3.11-slim

WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TF_CPP_MIN_LOG_LEVEL=2

# Optional extra CA certificates (certs/*.crt), e.g. when an antivirus or proxy
# inspects HTTPS. The folder may be empty.
COPY certs/ /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the ResNet50 ImageNet weights at build time so the container runs offline
COPY app/__init__.py app/settings.py app/model.py app/
RUN python -c "from app.model import build_backbone; build_backbone()"

COPY app app
COPY frontend frontend
COPY data data
COPY artifacts artifacts
COPY figures figures
COPY run.py .

EXPOSE 9100
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "9100"]
