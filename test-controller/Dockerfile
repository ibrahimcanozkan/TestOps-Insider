FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY test_controller.py .

RUN useradd -m -u 1000 testuser && \
    chown -R testuser:testuser /app
USER testuser

ENV PYTHONUNBUFFERED=1

CMD ["python", "test_controller.py"]