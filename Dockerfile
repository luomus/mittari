FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /opt/app-root/src

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

ENV PATH="/opt/app-root/src/.venv/bin:$PATH"

COPY app ./app
COPY wsgi.py .

# OpenShift may run the container with a random UID.
RUN chgrp -R 0 /opt/app-root/src && chmod -R g=u /opt/app-root/src

EXPOSE 8080

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers ${GUNICORN_WORKERS:-2} wsgi:app"]
