# Code-execution sandbox image. Build: docker build -t ai-coach-sandbox:latest infra/sandbox
FROM python:3.12-slim

# No pip, no network at runtime (--network none), runs as nobody (--user 65534).
# Keep the image minimal: stdlib only.
RUN rm -rf /root/.cache && apt-get purge -y --auto-remove || true

USER 65534:65534
WORKDIR /tmp
CMD ["python3"]
