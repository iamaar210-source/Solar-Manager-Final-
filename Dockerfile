FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && python -c "import gunicorn, flask; print('deps OK')"

COPY . .

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/code

EXPOSE 8000

# Use start.py so PORT is always read from the environment in Python
CMD ["python", "start.py"]
