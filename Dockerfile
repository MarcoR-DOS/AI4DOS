FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/server/src
WORKDIR /app
COPY server/requirements.txt server/requirements-lock.txt /app/server/
RUN python -m pip install --no-cache-dir -r server/requirements-lock.txt \
    && python -m pip check \
    && groupadd --gid 10001 ai4dos \
    && useradd --uid 10001 --gid ai4dos --no-create-home --shell /usr/sbin/nologin ai4dos \
    && mkdir /config
COPY server/src/ai4dos/ /app/server/src/ai4dos/
COPY tools/docker-healthcheck.py /app/tools/
USER 10001:10001
EXPOSE 1983
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "/app/tools/docker-healthcheck.py"]
STOPSIGNAL SIGINT
ENTRYPOINT ["python", "-m", "ai4dos.server"]
CMD ["--config", "/config/gateway.json", "--host", "0.0.0.0", "--port", "1983"]
