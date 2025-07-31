import { Router, Request, Response } from 'express';
import { authenticateToken, requireRole, requirePermission, AuthenticatedRequest } from '../middleware/auth';
import { defaultRateLimiter, authRateLimiter, readOnlyRateLimiter, tenantRateLimiter } from '../middleware/rateLimiter';
import { proxyService } from '../services/proxy.service';
import logger from '../utils/logger';

const router = Router();

// Health check endpoint (no authentication required)
router.get('/health', async (req: Request, res: Response) => {
  try {
    const healthStatuses = await proxyService.getAllHealthStatuses();
    const overallHealth = healthStatuses.every(status => status.status === 'healthy') ? 'healthy' : 'degraded';
    
    res.json({
      status: overallHealth,
      timestamp: new Date().toISOString(),
      services: healthStatuses,
      version: process.env.npm_package_version || '1.0.0',
    });
  } catch (error) {
    logger.error('Health check failed:', error);
    res.status(500).json({
      status: 'unhealthy',
      timestamp: new Date().toISOString(),
      error: 'Health check failed',
    });
  }
});

// API version info (no authentication required)
router.get('/api/v1/info', (req: Request, res: Response) => {
  res.json({
    service: 'api-gateway',
    version: process.env.npm_package_version || '1.0.0',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development',
  });
});

// Apply authentication and rate limiting to all API routes
router.use('/api/v1', authenticateToken);
router.use('/api/v1', tenantRateLimiter);

// Chat Service Routes
router.use('/api/v1/conversations*', defaultRateLimiter, (req: AuthenticatedRequest, res: Response) => {
  proxyService.proxyRequest('chat-service', req, res);
});

router.use('/api/v1/messages*', defaultRateLimiter, (req: AuthenticatedRequest, res: Response) => {
  proxyService.proxyRequest('chat-service', req, res);
});

router.use('/api/v1/chat*', defaultRateLimiter, (req: AuthenticatedRequest, res: Response) => {
  proxyService.proxyRequest('chat-service', req, res);
});

// Presence Service Routes
router.use('/api/v1/presence*', readOnlyRateLimiter, (req: AuthenticatedRequest, res: Response) => {
  proxyService.proxyRequest('presence-service', req, res);
});

router.use('/api/v1/agents*', readOnlyRateLimiter, (req: AuthenticatedRequest, res: Response) => {
  proxyService.proxyRequest('presence-service', req, res);
});

// Summary Engine Routes
router.use('/api/v1/summaries*', defaultRateLimiter, (req: AuthenticatedRequest, res: Response) => {
  proxyService.proxyRequest('summary-engine', req, res);
});

router.use('/api/v1/insights*', requireRole(['admin', 'supervisor']), defaultRateLimiter, (req: AuthenticatedRequest, res: Response) => {
  proxyService.proxyRequest('summary-engine', req, res);
});

// WebSocket Gateway Health (REST endpoint for WebSocket service health)
router.get('/api/v1/websocket/health', readOnlyRateLimiter, (req: AuthenticatedRequest, res: Response) => {
  proxyService.proxyRequest('websocket-gateway', req, res, '/health');
});

// Admin-only routes
router.use('/api/v1/admin*', 
  requireRole(['admin']), 
  defaultRateLimiter,
  (req: AuthenticatedRequest, res: Response) => {
    // Route admin requests to appropriate services based on path
    const path = req.path;
    
    if (path.includes('/admin/chat')) {
      proxyService.proxyRequest('chat-service', req, res);
    } else if (path.includes('/admin/presence')) {
      proxyService.proxyRequest('presence-service', req, res);
    } else if (path.includes('/admin/summaries')) {
      proxyService.proxyRequest('summary-engine', req, res);
    } else {
      res.status(404).json({ error: 'Admin endpoint not found' });
    }
  }
);

// Service-specific health endpoints (authenticated)
router.get('/api/v1/services/:serviceName/health', 
  readOnlyRateLimiter,
  async (req: AuthenticatedRequest, res: Response) => {
    const { serviceName } = req.params;
    
    try {
      const healthStatus = await proxyService.checkServiceHealth(serviceName);
      res.json(healthStatus);
    } catch (error) {
      logger.error(`Health check failed for service ${serviceName}:`, error);
      res.status(500).json({
        service: serviceName,
        status: 'unhealthy',
        error: 'Health check failed',
        timestamp: new Date().toISOString(),
      });
    }
  }
);

// Bulk health check for all services (authenticated)
router.get('/api/v1/services/health', 
  readOnlyRateLimiter,
  async (req: AuthenticatedRequest, res: Response) => {
    try {
      const healthStatuses = await proxyService.getAllHealthStatuses();
      res.json({
        timestamp: new Date().toISOString(),
        services: healthStatuses,
      });
    } catch (error) {
      logger.error('Bulk health check failed:', error);
      res.status(500).json({
        error: 'Bulk health check failed',
        timestamp: new Date().toISOString(),
      });
    }
  }
);

// Catch-all for unknown API routes
router.use('/api/v1/*', (req: Request, res: Response) => {
  logger.warn('Unknown API route accessed', {
    path: req.path,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('User-Agent'),
    userId: (req as AuthenticatedRequest).user?.id,
  });
  
  res.status(404).json({
    error: 'API endpoint not found',
    path: req.path,
    method: req.method,
  });
});

// Root endpoint
router.get('/', (req: Request, res: Response) => {
  res.json({
    service: 'chorus-api-gateway',
    message: 'Chorus API Gateway is running',
    version: process.env.npm_package_version || '1.0.0',
    timestamp: new Date().toISOString(),
    docs: '/api/v1/info',
  });
});

export default router;