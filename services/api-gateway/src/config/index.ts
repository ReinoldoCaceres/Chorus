import dotenv from 'dotenv';

dotenv.config();

export const config = {
  server: {
    port: parseInt(process.env.PORT || '8084'),
    host: process.env.HOST || '0.0.0.0',
  },
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD,
  },
  auth: {
    jwtSecret: process.env.JWT_SECRET || 'your-secret-key',
    jwtExpiresIn: process.env.JWT_EXPIRES_IN || '6h',
  },
  services: {
    chatService: {
      url: process.env.CHAT_SERVICE_URL || 'http://localhost:8082',
      timeout: parseInt(process.env.CHAT_SERVICE_TIMEOUT || '30000'),
    },
    presenceService: {
      url: process.env.PRESENCE_SERVICE_URL || 'http://localhost:8081',
      timeout: parseInt(process.env.PRESENCE_SERVICE_TIMEOUT || '30000'),
    },
    summaryEngine: {
      url: process.env.SUMMARY_ENGINE_URL || 'http://localhost:8083',
      timeout: parseInt(process.env.SUMMARY_ENGINE_TIMEOUT || '30000'),
    },
    websocketGateway: {
      url: process.env.WEBSOCKET_GATEWAY_URL || 'http://localhost:8080',
      timeout: parseInt(process.env.WEBSOCKET_GATEWAY_TIMEOUT || '30000'),
    },
  },
  rateLimiting: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000'), // 15 minutes
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100'),
    skipSuccessfulRequests: process.env.RATE_LIMIT_SKIP_SUCCESSFUL === 'true',
  },
  cors: {
    origin: process.env.CORS_ORIGIN?.split(',') || ['http://localhost:3000'],
    credentials: true,
  },
  logging: {
    level: process.env.LOG_LEVEL || 'info',
  },
  health: {
    checkIntervalMs: parseInt(process.env.HEALTH_CHECK_INTERVAL_MS || '30000'),
  },
};