import { Request, Response } from 'express';
import axios, { AxiosResponse, AxiosError } from 'axios';
import { config } from '../config';
import logger from '../utils/logger';

export interface ServiceConfig {
  url: string;
  timeout: number;
}

export interface HealthStatus {
  service: string;
  status: 'healthy' | 'unhealthy';
  responseTime?: number;
  error?: string;
  timestamp: string;
}

class ProxyService {
  private services: Record<string, ServiceConfig>;
  private healthCache: Map<string, HealthStatus> = new Map();
  private healthCheckInterval: NodeJS.Timeout | null = null;

  constructor() {
    this.services = {
      'chat-service': config.services.chatService,
      'presence-service': config.services.presenceService,
      'summary-engine': config.services.summaryEngine,
      'websocket-gateway': config.services.websocketGateway,
    };

    // Start health check monitoring
    this.startHealthChecks();
  }

  async proxyRequest(
    serviceName: string,
    req: Request,
    res: Response,
    path?: string
  ): Promise<void> {
    const serviceConfig = this.services[serviceName];
    
    if (!serviceConfig) {
      logger.error(`Unknown service: ${serviceName}`);
      res.status(404).json({ error: 'Service not found' });
      return;
    }

    // Check service health before proxying
    const healthStatus = this.healthCache.get(serviceName);
    if (healthStatus?.status === 'unhealthy') {
      logger.warn(`Service ${serviceName} is unhealthy, request may fail`);
    }

    const targetPath = path || req.path;
    const targetUrl = `${serviceConfig.url}${targetPath}`;
    
    const startTime = Date.now();
    
    try {
      logger.debug(`Proxying request to ${serviceName}`, {
        targetUrl,
        method: req.method,
        userAgent: req.get('User-Agent'),
        userId: (req as any).user?.id,
        tenantId: (req as any).user?.tenantId,
      });

      // Prepare headers, excluding hop-by-hop headers
      const proxyHeaders = { ...req.headers };
      delete proxyHeaders.host;
      delete proxyHeaders.connection;
      delete proxyHeaders['content-length'];

      const axiosConfig = {
        method: req.method.toLowerCase() as any,
        url: targetUrl,
        headers: proxyHeaders,
        timeout: serviceConfig.timeout,
        validateStatus: () => true, // Don't throw on HTTP error status codes
        data: ['GET', 'HEAD'].includes(req.method.toUpperCase()) ? undefined : req.body,
        params: req.query,
      };

      const response: AxiosResponse = await axios(axiosConfig);
      const responseTime = Date.now() - startTime;

      logger.debug(`Proxy response from ${serviceName}`, {
        targetUrl,
        status: response.status,
        responseTime,
        contentType: response.headers['content-type'],
      });

      // Forward response headers (excluding hop-by-hop headers)
      Object.keys(response.headers).forEach((key) => {
        if (!['connection', 'keep-alive', 'transfer-encoding'].includes(key.toLowerCase())) {
          res.set(key, response.headers[key]);
        }
      });

      // Add custom headers for debugging
      res.set('X-Proxied-By', 'api-gateway');
      res.set('X-Response-Time', `${responseTime}ms`);
      res.set('X-Target-Service', serviceName);

      res.status(response.status).send(response.data);

    } catch (error) {
      const responseTime = Date.now() - startTime;
      
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError;
        
        logger.error(`Proxy request failed for ${serviceName}`, {
          targetUrl,
          error: axiosError.message,
          code: axiosError.code,
          responseTime,
          status: axiosError.response?.status,
        });

        if (axiosError.code === 'ECONNREFUSED' || axiosError.code === 'ETIMEDOUT') {
          res.status(503).json({
            error: 'Service temporarily unavailable',
            service: serviceName,
            message: 'The requested service is currently not responding',
          });
        } else if (axiosError.response) {
          // Forward the error response from the downstream service
          res.status(axiosError.response.status).send(axiosError.response.data);
        } else {
          res.status(502).json({
            error: 'Bad gateway',
            service: serviceName,
            message: 'Error communicating with downstream service',
          });
        }
      } else {
        logger.error(`Unexpected error proxying to ${serviceName}`, {
          targetUrl,
          error: error instanceof Error ? error.message : 'Unknown error',
          responseTime,
        });

        res.status(500).json({
          error: 'Internal server error',
          message: 'An unexpected error occurred while processing your request',
        });
      }
    }
  }

  async checkServiceHealth(serviceName: string): Promise<HealthStatus> {
    const serviceConfig = this.services[serviceName];
    const startTime = Date.now();

    try {
      const response = await axios.get(`${serviceConfig.url}/health`, {
        timeout: 5000, // Short timeout for health checks
      });

      const responseTime = Date.now() - startTime;
      const status: HealthStatus = {
        service: serviceName,
        status: response.status === 200 ? 'healthy' : 'unhealthy',
        responseTime,
        timestamp: new Date().toISOString(),
      };

      return status;
    } catch (error) {
      const responseTime = Date.now() - startTime;
      const status: HealthStatus = {
        service: serviceName,
        status: 'unhealthy',
        responseTime,
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      };

      return status;
    }
  }

  async getAllHealthStatuses(): Promise<HealthStatus[]> {
    const healthPromises = Object.keys(this.services).map(serviceName =>
      this.checkServiceHealth(serviceName)
    );

    const healthStatuses = await Promise.all(healthPromises);
    
    // Update cache
    healthStatuses.forEach(status => {
      this.healthCache.set(status.service, status);
    });

    return healthStatuses;
  }

  private startHealthChecks(): void {
    // Initial health check
    this.getAllHealthStatuses().catch(error => {
      logger.error('Initial health check failed:', error);
    });

    // Periodic health checks
    this.healthCheckInterval = setInterval(async () => {
      try {
        await this.getAllHealthStatuses();
        logger.debug('Health check completed for all services');
      } catch (error) {
        logger.error('Periodic health check failed:', error);
      }
    }, config.health.checkIntervalMs);
  }

  getHealthStatus(serviceName: string): HealthStatus | undefined {
    return this.healthCache.get(serviceName);
  }

  getAllCachedHealthStatuses(): HealthStatus[] {
    return Array.from(this.healthCache.values());
  }

  stop(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }
}

export const proxyService = new ProxyService();