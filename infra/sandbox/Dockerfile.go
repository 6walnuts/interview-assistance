# Build: docker build -t ai-coach-sandbox-go:latest -f Dockerfile.go .
FROM golang:1.23
USER 65534:65534
WORKDIR /tmp
