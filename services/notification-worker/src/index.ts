import { NotificationWorker } from './workers/notification.worker';
import emailService from './services/email.service';
import smsService from './services/sms.service';
import pushService from './services/push.service';
import logger from './services/logger';

async function main() {
  try {
    logger.info('Initializing notification worker...');

    // Verify service connections
    const emailOk = await emailService.verifyConnection();
    const smsOk = await smsService.verifyConnection();
    const pushOk = await pushService.verifyConnection();

    if (!emailOk) {
      logger.warn('Email service not available');
    }
    if (!smsOk) {
      logger.warn('SMS service not available');
    }
    if (!pushOk) {
      logger.warn('Push service not available');
    }

    // Create and start worker
    const worker = new NotificationWorker();
    await worker.start();

    // Handle graceful shutdown
    const shutdown = async () => {
      logger.info('Received shutdown signal');
      await worker.stop();
      process.exit(0);
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);

  } catch (error) {
    logger.error('Failed to start notification worker', { error });
    process.exit(1);
  }
}

main();