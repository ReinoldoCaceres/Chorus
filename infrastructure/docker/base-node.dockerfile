# Base Node.js Dockerfile for Chorus Platform
FROM node:18-alpine as base

# Set environment variables
ENV NODE_ENV=development

# Install system dependencies
RUN apk add --no-cache \
    curl \
    netcat-openbsd \
    && rm -rf /var/cache/apk/*

# Create non-root user
RUN addgroup -g 1001 -S chorus && \
    adduser -S chorus -u 1001

# Set work directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies (use npm install if package-lock.json doesn't exist)
RUN if [ -f package-lock.json ]; then \
        npm ci --omit=dev && npm cache clean --force; \
    else \
        npm install --omit=dev && npm cache clean --force; \
    fi

# Development stage
FROM base as development

# Install all dependencies including dev dependencies
RUN if [ -f package-lock.json ]; then \
        npm ci && npm cache clean --force; \
    else \
        npm install && npm cache clean --force; \
    fi

# Copy application code
COPY . .

# Change ownership to non-root user
RUN chown -R chorus:chorus /app

# Switch to non-root user
USER chorus

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

# Default command for development
CMD ["npm", "run", "dev"]

# Production stage
FROM base as production

ARG BUILD_MODE=production

# Copy application code
COPY . .

# Build application if needed
RUN if [ "$BUILD_MODE" = "production" ]; then npm run build 2>/dev/null || echo "No build script found"; fi

# Change ownership to non-root user
RUN chown -R chorus:chorus /app

# Switch to non-root user
USER chorus

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-3000}/health || exit 1

# Default command for production
CMD ["npm", "start"]