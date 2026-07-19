# Build: docker build -t ai-coach-sandbox-cpp:latest -f Dockerfile.cpp .
FROM gcc:13
USER 65534:65534
WORKDIR /tmp
