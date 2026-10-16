# Multi-stage image: build the React UI, then serve API + static UI from one FastAPI process.
# Research-only tool; no broker connectivity is built in.
FROM node:20-alpine AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    FXLAB_DB=/data/fxlab.sqlite3 FXLAB_STATIC_DIR=/app/frontend/dist \
    FXLAB_CORS_ORIGINS="" FXLAB_MAX_UPLOAD_MB=250
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ /app/backend/
COPY config/ /app/config/
COPY docs/ /app/docs/
COPY README.md DISCLAIMER.md LICENSE /app/
COPY --from=ui /ui/dist /app/frontend/dist
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}
RUN mkdir -p /data && useradd --create-home fxlab && chown -R fxlab /data /app
USER fxlab
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
