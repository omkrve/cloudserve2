
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CLOUDSERVE_DATA_DIR=/var/lib/cloudserve/data
ENV CLOUDSERVE_UPLOAD_DIR=/var/lib/cloudserve/uploads

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates ./templates
COPY static ./static

RUN useradd --create-home appuser \
    && mkdir -p /var/lib/cloudserve/data /var/lib/cloudserve/uploads \
    && chown -R appuser:appuser /var/lib/cloudserve

USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
