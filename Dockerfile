FROM python:3.12-slim

WORKDIR /code

# Install deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "import gunicorn; import flask; print('deps OK')"

COPY . .

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

EXPOSE 8000

# Prefer gunicorn; verify it exists at build time already
CMD ["sh", "-c", "python -c 'import gunicorn' && gunicorn wsgi:app --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --timeout 120 --access-logfile - --error-logfile -"]
