# Build: docker build -t ai-coach-sandbox-javascript:latest -f Dockerfile.javascript .
FROM node:22-slim
USER 65534:65534
WORKDIR /tmp
