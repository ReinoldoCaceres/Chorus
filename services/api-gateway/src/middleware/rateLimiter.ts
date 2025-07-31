import rateLimit from 'express-rate-limit';
import { createClient } from 'redis';
import { config } from '../config';
import logger from '../utils/logger';

// Redis client for rate limiting storage
let redisClient: any = null;

const initializeRedis = async () => {
  if (!redisClient) {
    redisClient = createClient({
      socket: {
        host: config.redis.host,
        port: config.redis.port,
      },
      password: config.redis.password,
    });

    redisClient.on('error', (err: Error) => {
      logger.error('Redis client error for rate limiter:', err);
    });

    redisClient.on('connect', () => {
      logger.info('Redis connected for rate limiting');
    });

    await redisClient.connect();
  }
  return redisClient;
};

// Custom store using Redis for distributed rate limiting
class RedisStore {
  private prefix: string;
  private client: any;

  constructor(prefix = 'rl:') {
    this.prefix = prefix;
  }

  async init() {
    this.client = await initializeRedis();
  }

  async increment(key: string, ttl: number) {
    if (!this.client) {
      await this.init();
    }

    const fullKey = this.prefix + key;
    
    try {
      const multi = this.client.multi();
      multi.incr(fullKey);
      multi.expire(fullKey, Math.ceil(ttl / 1000));
      const results = await multi.exec();
      
      const count = results[0];
      return {
        totalHits: count,
        resetTime: new Date(Date.now() + ttl),
      };
    } catch (error) {
      logger.error('Redis rate limiter error:', error);
      // Fallback to memory-based limiting if Redis fails
      throw error;
    }
  }

  async decrement(key: string) {
    if (!this.client) {
      await this.init();
    }

    const fullKey = this.prefix + key;
    
    try {
      const count = await this.client.decr(fullKey);
      return count;
    } catch (error) {
      logger.error('Redis rate limiter decrement error:', error);
    }
  }

  async resetKey(key: string) {
    if (!this.client) {
      await this.init();
    }

    const fullKey = this.prefix + key;
    
    try {
      await this.client.del(fullKey);
    } catch (error) {
      logger.error('Redis rate limiter reset error:', error);
    }
  }
}

// Create rate limiter with Redis store
export const createRateLimiter = (
  windowMs: number = config.rateLimiting.windowMs,
  maxRequests: number = config.rateLimiting.maxRequests,
  keyGenerator?: (req: any) => string
) => {
  const redisStore = new RedisStore();

  return rateLimit({
    windowMs,
    max: maxRequests,
    message: {
      error: 'Too many requests from this IP, please try again later.',
      retryAfter: Math.ceil(windowMs / 1000),
    },
    standardHeaders: true,
    legacyHeaders: false,
    keyGenerator: keyGenerator || ((req) => {
      // Use IP + User ID if authenticated, otherwise just IP
      const baseKey = req.ip;
      const userId = req.user?.id;
      return userId ? `${baseKey}:${userId}` : baseKey;
    }),
    skip: (req) => {
      // Skip rate limiting for health checks
      return req.path === '/health' || req.path === '/api/v1/health';
    },
    onLimitReached: (req, res, options) => {
      logger.warn('Rate limit exceeded', {
        ip: req.ip,
        path: req.path,
        userAgent: req.get('User-Agent'),
        userId: req.user?.id,
        limit: maxRequests,
        windowMs,
      });
    },
    // Use memory store as fallback if Redis is not available
    // In production, you might want to implement a proper Redis store
    skipSuccessfulRequests: config.rateLimiting.skipSuccessfulRequests,
  });
};

// Default rate limiter for general API usage
export const defaultRateLimiter = createRateLimiter();

// Stricter rate limiter for authentication endpoints
export const authRateLimiter = createRateLimiter(
  15 * 60 * 1000, // 15 minutes
  5 // 5 attempts per 15 minutes
);

// More lenient rate limiter for read operations
export const readOnlyRateLimiter = createRateLimiter(
  15 * 60 * 1000, // 15 minutes
  300 // 300 requests per 15 minutes
);

// Per-tenant rate limiter
export const tenantRateLimiter = createRateLimiter(
  15 * 60 * 1000, // 15 minutes
  1000, // 1000 requests per tenant per 15 minutes
  (req) => `tenant:${req.user?.tenantId || 'anonymous'}`
);