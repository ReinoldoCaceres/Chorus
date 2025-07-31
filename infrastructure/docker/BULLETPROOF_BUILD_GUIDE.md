# Bulletproof Docker Build Strategy for Go Services

This guide explains the production-grade Docker build strategy implemented for Chorus Platform Go services. The strategy is designed to be bulletproof, handling missing `go.sum` files gracefully while following Google-level Docker best practices.

## 🚀 Key Features

- **Zero-dependency on pre-existing go.sum files**
- **Automatic checksum generation and verification**
- **Production-grade security with non-root user**
- **Optimal layer caching for fast rebuilds**
- **Multi-stage builds for minimal production images**
- **Comprehensive build validation and error handling**

## 📁 Files Overview

### Core Files
- `base-go.dockerfile` - Bulletproof multi-stage Dockerfile
- `build-go-service.sh` - Enhanced build script with validation
- `.dockerignore` - Optimized build context exclusions

## 🛠️ How It Works

### The Bulletproof Strategy

1. **Graceful go.sum Handling**: The Dockerfile copies the entire source code, allowing Go to naturally handle `go.sum` whether it exists or not
2. **Natural Dependency Resolution**: Uses `go mod download` and `go mod tidy` to ensure consistency
3. **Checksum Verification**: Always verifies module checksums regardless of initial state
4. **Build Cache Optimization**: Leverages Docker layer caching for maximum efficiency

### Build Stages

```
base stage
├── Dependency resolution
├── Checksum verification  
├── Module consistency check
└── Build cache optimization

development stage (extends base)
├── Hot reload capability
├── Development tools
└── Health checks

builder stage (extends base)  
├── Optimized production build
├── Static binary generation
└── Security hardening

production stage
├── Minimal Alpine base
├── Non-root user security
├── Health checks
└── Production runtime
```

## 🎯 Usage Examples

### Basic Build
```bash
# Build production image
./build-go-service.sh websocket-gateway

# Build development image  
./build-go-service.sh websocket-gateway development

# Build with custom flags
./build-go-service.sh presence-service production --no-cache
```

### Advanced Usage
```bash
# Build with progress output
./build-go-service.sh websocket-gateway production --progress=plain

# Build all stages for testing
for stage in base development builder production; do
    ./build-go-service.sh websocket-gateway $stage
done
```

## 🔒 Security Features

- **Non-root user execution** (UID/GID 1001)
- **Minimal attack surface** in production stage
- **Static binary compilation** with security flags
- **No sensitive files in build context** (via .dockerignore)
- **Checksum verification** for all dependencies
- **Security labels** following OCI standards

## ⚡ Performance Optimizations

- **Docker BuildKit** enabled by default
- **Inline cache** for faster rebuilds
- **Optimized layer ordering** for maximum cache hits
- **Trimpath compilation** for smaller binaries
- **Static linking** for portable executables

## 🧪 Testing the Strategy

### Test with Missing go.sum
```bash
# Remove go.sum and test build
cd services/websocket-gateway
mv go.sum go.sum.backup
../../infrastructure/docker/build-go-service.sh websocket-gateway
```

### Test with Existing go.sum
```bash
# Restore go.sum and test build
cd services/websocket-gateway  
mv go.sum.backup go.sum
../../infrastructure/docker/build-go-service.sh websocket-gateway
```

### Verify Build Security
```bash
# Check final image runs as non-root
docker run --rm chorus/websocket-gateway:production id

# Verify static binary
docker run --rm chorus/websocket-gateway:production file /app/main
```

## 🚨 Troubleshooting

### Build Context Too Large
- Review `.dockerignore` exclusions
- Remove unnecessary files from service directory
- Use `docker system df` to check build cache usage

### Dependency Resolution Issues
- Ensure `go.mod` is valid and in service root
- Check network connectivity for module downloads
- Verify GOPROXY settings if using private modules

### Permission Errors
- Ensure build script is executable: `chmod +x build-go-service.sh`
- Check Docker daemon permissions
- Verify service directory ownership

## 🎛️ Environment Variables

The Dockerfile supports these environment variables:

```dockerfile
CGO_ENABLED=0          # Disable CGO for static builds
GOOS=linux            # Target Linux OS
GOARCH=amd64          # Target AMD64 architecture  
GOPROXY=...           # Go module proxy
GOSUMDB=...           # Go checksum database
GOCACHE=/go-cache     # Go build cache location
```

## 📊 Build Metrics

The build script provides detailed metrics:
- Build time and image size
- Layer optimization insights
- Security compliance status
- Dependency verification results

## 🔄 Continuous Integration

For CI/CD pipelines:
```yaml
# Example GitHub Actions step
- name: Build Go Service
  run: |
    ./infrastructure/docker/build-go-service.sh websocket-gateway production
  env:
    DOCKER_BUILDKIT: 1
```

## 📈 Best Practices

1. **Always use the build script** rather than docker build directly
2. **Test both scenarios** (with and without go.sum)
3. **Monitor image sizes** and optimize when needed
4. **Use specific stage targets** for different environments
5. **Leverage build cache** in CI/CD for faster builds

## 🆘 Support

For issues with the bulletproof build strategy:
1. Check the build script output for specific error messages
2. Verify all prerequisites are met
3. Test with a minimal Go service first
4. Review Docker and Go versions for compatibility

---

**Status**: ✅ Production Ready  
**Last Updated**: $(date -u +'%Y-%m-%d')  
**Compatibility**: Go 1.21+, Docker 20.10+, BuildKit