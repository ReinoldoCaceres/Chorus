# Docker Build Strategy - Go Services

This directory contains optimized Docker build configurations for Go services in the Chorus platform.

## Overview

The Docker build strategy implements Google-level best practices for Go applications, focusing on:

- **Optimal layer caching** for Go modules
- **Multi-stage builds** for minimal production images
- **Security-first approach** with non-root users
- **Reproducible builds** with dependency verification
- **Production-grade optimizations**

## Files

- `base-go.dockerfile` - Optimized multi-stage Dockerfile for Go services
- `.dockerignore` - Build context optimization
- `build-go-service.sh` - Build automation script
- `README.md` - This documentation

## Architecture

### Multi-Stage Build Strategy

```
┌─────────────────┐
│   base stage    │  ← Dependency resolution & caching
│  (go mod deps)  │
└─────────────────┘
         │
         ├─────────────────┐
         │                 │
┌─────────────────┐ ┌─────────────────┐
│ development     │ │   builder       │
│   stage         │ │   stage         │
└─────────────────┘ └─────────────────┘
                           │
                    ┌─────────────────┐
                    │  production     │
                    │    stage        │
                    └─────────────────┘
```

### Key Optimizations

#### 1. Dependency Resolution Strategy

```dockerfile
# Base stage - Optimal caching layer
COPY --chown=chorus:chorus go.mod go.sum ./
RUN go mod download && go mod verify
```

**Benefits:**
- Dependencies cached in separate layer
- Only rebuilds when `go.mod`/`go.sum` changes
- Verified dependency integrity

#### 2. Source Code Handling

```dockerfile
# Copy all source code
COPY --chown=chorus:chorus . .

# Remove go.mod/go.sum to prevent overwriting resolved dependencies
RUN rm -f go.mod go.sum

# Restore resolved dependencies from base layer
COPY --from=base --chown=chorus:chorus /app/go.mod /app/go.sum ./
```

**Benefits:**
- Preserves resolved dependencies across stages
- Prevents file conflicts between build contexts
- Maintains dependency consistency

#### 3. Build Optimizations

```dockerfile
RUN go build \
    -ldflags='-w -s -extldflags "-static"' \
    -a \
    -installsuffix cgo \
    -tags netgo \
    -o main .
```

**Flags Explained:**
- `-ldflags='-w -s'` - Strip debug info and symbol table
- `-extldflags "-static"` - Static linking
- `-tags netgo` - Pure Go network stack
- `-installsuffix cgo` - Separate package cache

#### 4. Security Features

- **Non-root user** throughout all stages
- **Minimal attack surface** with Alpine Linux
- **Static binary** with no external dependencies
- **Proper file ownership** with `--chown` flags

## Usage

### Using the Build Script

```bash
# Build production image
./build-go-service.sh websocket-gateway

# Build development image
./build-go-service.sh presence-service development

# Build with additional Docker options
./build-go-service.sh workflow-engine production --no-cache
```

### Manual Docker Build

```bash
# From service directory
cd services/websocket-gateway

# Copy .dockerignore
cp ../../infrastructure/docker/.dockerignore .

# Build production image
docker build \
  -f ../../infrastructure/docker/base-go.dockerfile \
  --target production \
  -t chorus/websocket-gateway:production \
  .
```

### Available Stages

1. **base** - Dependencies only (for debugging)
2. **development** - Development environment with source code
3. **builder** - Build stage (intermediate)
4. **production** - Minimal production runtime

## Environment Variables

### Build-time Variables

- `CGO_ENABLED=0` - Disable CGO for static builds
- `GOOS=linux` - Target Linux OS
- `GOARCH=amd64` - Target AMD64 architecture
- `GO111MODULE=on` - Enable Go modules
- `GOPROXY` - Go module proxy configuration
- `GOSUMDB` - Checksum database for verification

### Runtime Variables

- `PORT` - Application port (default: 8081)

## Performance Characteristics

### Build Performance

- **Layer caching**: Dependencies cached separately from source code
- **Parallel builds**: Multi-stage builds enable parallel execution
- **Minimal context**: `.dockerignore` reduces build context size

### Runtime Performance

- **Static binary**: No runtime dependencies
- **Minimal image**: ~20MB production images
- **Fast startup**: Pre-compiled binary with optimizations

## Security Considerations

### Build Security

- **Dependency verification**: `go mod verify` ensures integrity
- **Reproducible builds**: Locked dependency versions
- **Minimal attack surface**: Alpine base with minimal packages

### Runtime Security

- **Non-root execution**: User `chorus` (UID 1001)
- **Read-only filesystem** compatible
- **No shell access** in production images

## Troubleshooting

### Common Issues

#### go.mod/go.sum Conflicts

**Problem**: Build fails with module resolution errors

**Solution**: Ensure `go.mod` and `go.sum` are consistent:

```bash
go mod tidy
go mod verify
```

#### Permission Errors

**Problem**: Permission denied in container

**Solution**: Check `--chown` flags in COPY instructions:

```dockerfile
COPY --chown=chorus:chorus . .
```

#### Large Image Size

**Problem**: Production images are too large

**Solution**: 
- Use multi-stage builds (production stage)
- Enable static linking flags
- Remove debug symbols with `-ldflags='-w -s'`

### Debugging

#### Inspect Build Stages

```bash
# Build specific stage
docker build --target base -t debug/base .

# Run interactive container
docker run -it debug/base sh
```

#### Check Dependencies

```bash
# Verify modules
docker run -it chorus/service:production go mod verify

# List dependencies
docker run -it chorus/service:development go list -m all
```

## Best Practices

### Development Workflow

1. **Use development stage** for local development
2. **Mount source code** for hot reload:
   ```bash
   docker run -v $(pwd):/app chorus/service:development
   ```

### Production Deployment

1. **Use production stage** for deployments
2. **Multi-arch builds** for different platforms:
   ```bash
   docker buildx build --platform linux/amd64,linux/arm64
   ```

### CI/CD Integration

```yaml
# Example GitHub Actions
- name: Build Docker image
  run: |
    ./infrastructure/docker/build-go-service.sh ${{ matrix.service }} production
```

## Monitoring

### Build Metrics

- **Build time**: Track build duration for optimization
- **Layer cache hit rate**: Monitor caching effectiveness
- **Image size**: Track production image sizes

### Runtime Metrics

- **Container startup time**: Monitor application boot time
- **Memory usage**: Track runtime memory consumption
- **CPU usage**: Monitor processing overhead

## Migration Guide

### From Previous Dockerfile

1. **Update build commands** to use new script
2. **Copy .dockerignore** to service directories
3. **Update CI/CD pipelines** to use new build process
4. **Test all build stages** ensure compatibility

### Service-Specific Adaptations

For services with additional dependencies:

```dockerfile
# Add after base stage, before COPY source
RUN apk add --no-cache additional-package
```

## Support

For issues or questions about the Docker build strategy:

1. Check troubleshooting section above
2. Review Docker build logs for specific errors
3. Validate go.mod/go.sum consistency
4. Ensure proper file permissions and ownership