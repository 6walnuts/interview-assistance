# Build: docker build -t ai-coach-sandbox-java:latest -f Dockerfile.java .
FROM eclipse-temurin:21-jdk-jammy
USER 65534:65534
WORKDIR /tmp
