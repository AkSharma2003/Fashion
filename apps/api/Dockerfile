FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
# Non-root user; it owns /srv so the app can create /srv/media (local profile photos).
RUN useradd --create-home --uid 10001 app && mkdir -p /srv/media && chown -R app:app /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
