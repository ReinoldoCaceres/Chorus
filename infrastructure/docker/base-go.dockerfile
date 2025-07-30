# Base Go Dockerfile for Chorus Platform
FROM golang:1.21-alpine as base

# Set environment variables
ENV CGO_ENABLED=0 \
    GOOS=linux \
    GOARCH=amd64

# Install system dependencies
RUN apk add --no-cache \
    git \
    ca-certificates \
    curl \
    netcat-openbsd \
    && update-ca-certificates

# Create non-root user
RUN addgroup -g 1001 -S chorus && \
    adduser -S chorus -u 1001

# Set work directory
WORKDIR /app

# Copy go mod files first for better caching
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download && go mod verify

# Development stage
FROM base as development

# Copy source code
COPY . .

# Change ownership to non-root user
RUN chown -R chorus:chorus /app

# Switch to non-root user
USER chorus

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8081}/health || exit 1

# Command to run in development mode with hot reload
CMD ["go", "run", "main.go"]

# Build stage
FROM base as builder

# Copy source code
COPY . .

# Build the application
RUN go build -a -installsuffix cgo -o main .

# Production stage
FROM alpine:latest as production

# Install ca-certificates for HTTPS requests
RUN apk --no-cache add ca-certificates curl netcat-openbsd

# Create non-root user
RUN addgroup -g 1001 -S chorus && \
    adduser -S chorus -u 1001

# Set work directory
WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/main .

# Change ownership to non-root user
RUN chown chorus:chorus main

# Switch to non-root user
USER chorus

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8081}/health || exit 1

# Command to run the application
CMD ["./main"]