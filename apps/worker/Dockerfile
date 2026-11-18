FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
RUN useradd --create-home --uid 10001 app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
USER app
CMD ["celery", "-A", "app.celery_app", "worker", "-B", "--loglevel=info"]
