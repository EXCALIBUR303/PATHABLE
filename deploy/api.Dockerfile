FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
COPY backend/requirements.lock /tmp/requirements.lock
COPY --from=wheels / /wheels
RUN --network=none python -m venv /venv && /venv/bin/pip install --no-index --find-links=/wheels --no-cache-dir --require-hashes -r /tmp/requirements.lock && /venv/bin/pip check

FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e
ENV PATH="/venv/bin:${PATH}" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=dependencies /venv /venv
COPY --chmod=755 backend /app/backend
WORKDIR /app/backend
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers", "--no-access-log", "--timeout-graceful-shutdown", "20"]
