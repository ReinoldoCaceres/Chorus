import twilio from 'twilio';
import { config } from '../config';
import logger from './logger';

interface SMSOptions {
  to: string;
  body: string;
}

class SMSService {
  private client: twilio.Twilio;

  constructor() {
    this.client = twilio(config.twilio.accountSid, config.twilio.authToken);
  }

  async sendSMS(options: SMSOptions): Promise<void> {
    try {
      const message = await this.client.messages.create({
        body: options.body,
        from: config.twilio.phoneNumber,
        to: options.to,
      });

      logger.info('SMS sent successfully', { messageSid: message.sid, to: options.to });
    } catch (error) {
      logger.error('Failed to send SMS', { error, to: options.to });
      throw error;
    }
  }

  async verifyConnection(): Promise<boolean> {
    try {
      await this.client.api.accounts(config.twilio.accountSid).fetch();
      logger.info('SMS service connection verified');
      return true;
    } catch (error) {
      logger.error('SMS service connection failed', { error });
      return false;
    }
  }
}

export default new SMSService();