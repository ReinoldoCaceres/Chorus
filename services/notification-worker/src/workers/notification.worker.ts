import { Worker, Job } from 'bullmq';
import { config } from '../config';
import emailService from '../services/email.service';
import smsService from '../services/sms.service';
import pushService from '../services/push.service';
import logger from '../services/logger';

export interface NotificationJobData {
  type: 'email' | 'sms' | 'push';
  recipient: string;
  subject?: string;
  body: string;
  html?: string;
  data?: Record<string, any>;
  retryCount?: number;
}

export class NotificationWorker {
  private worker: Worker;

  constructor() {
    this.worker = new Worker(
      config.worker.queueName,
      async (job: Job<NotificationJobData>) => {
        return this.processNotification(job);
      },
      {
        connection: {
          host: config.redis.host,
          port: config.redis.port,
          password: config.redis.password,
        },
        concurrency: config.worker.concurrency,
      }
    );

    this.setupEventHandlers();
  }

  private async processNotification(job: Job<NotificationJobData>) {
    const { type, recipient, subject, body, html, data } = job.data;

    logger.info('Processing notification', {
      jobId: job.id,
      type,
      recipient,
    });

    try {
      switch (type) {
        case 'email':
          await emailService.sendEmail({
            to: recipient,
            subject: subject || 'Notification',
            html: html || body,
            text: body,
          });
          break;

        case 'sms':
          await smsService.sendSMS({
            to: recipient,
            body,
          });
          break;

        case 'push':
          await pushService.sendPush({
            token: recipient,
            title: subject || 'Notification',
            body,
            data,
          });
          break;

        default:
          throw new Error(`Unknown notification type: ${type}`);
      }

      logger.info('Notification processed successfully', {
        jobId: job.id,
        type,
      });

      return { success: true, processedAt: new Date() };
    } catch (error) {
      logger.error('Failed to process notification', {
        jobId: job.id,
        type,
        error,
      });
      throw error;
    }
  }

  private setupEventHandlers() {
    this.worker.on('completed', (job) => {
      logger.info('Job completed', { jobId: job.id });
    });

    this.worker.on('failed', (job, err) => {
      logger.error('Job failed', {
        jobId: job?.id,
        error: err.message,
        stack: err.stack,
      });
    });

    this.worker.on('error', (err) => {
      logger.error('Worker error', { error: err });
    });

    this.worker.on('ready', () => {
      logger.info('Worker is ready and waiting for jobs');
    });
  }

  async start() {
    logger.info('Starting notification worker...');
    await this.worker.waitUntilReady();
    logger.info('Notification worker started successfully');
  }

  async stop() {
    logger.info('Stopping notification worker...');
    await this.worker.close();
    logger.info('Notification worker stopped');
  }
}