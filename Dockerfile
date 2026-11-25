# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /build/app/frontend
COPY app/frontend/package.json app/frontend/package-lock.json ./
RUN npm ci
COPY app/frontend/ ./
COPY app/itd/web_assets/logo.svg ../itd/web_assets/logo.svg
RUN mkdir -p ../itd/web_assets && npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ITD_PUBLIC_ORIGIN=http://127.0.0.1:8765
WORKDIR /srv/itd
# LibreOffice supplies DOCX previews; fonts cover Cyrillic document templates.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-writer fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 itd \
    && useradd --uid 10001 --gid itd --create-home itd
COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir -r app/requirements.txt
COPY app/ app/
COPY ai/ ai/
COPY run.py ./
COPY --from=frontend /build/app/itd/web_assets/ app/itd/web_assets/
RUN mkdir -p /data/db /data/logs \
    && chown -R itd:itd /data app/templates \
    && ln -s /data/logs logs
USER itd
VOLUME ["/data", "/srv/itd/app/templates"]
EXPOSE 8765
ENTRYPOINT ["python", "run.py"]
CMD ["--db", "/data/db/itd.db", "--host", "0.0.0.0", "--port", "8765", "--no-browser"]
