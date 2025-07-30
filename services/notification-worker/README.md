# Notification Worker

A Node.js worker service for processing notifications in the Chorus platform using BullMQ.

## Features

- **Email Notifications**: SMTP-based email sending with Nodemailer
- **SMS Notifications**: SMS sending via Twilio API
- **Push Notifications**: Push notification handling (extensible)
- **Queue Processing**: Redis-backed job queue with BullMQ
- **Error Handling**: Comprehensive error handling and logging
- **Retry Logic**: Automatic retry for failed notifications
- **TypeScript**: Full TypeScript support

## Setup

### Prerequisites

- Node.js 20+
- Redis server
- SMTP server access (for email)
- Twilio account (for SMS)

### Installation

```bash
npm install
```

### Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Configure the following environment variables:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your-email@example.com
SMTP_PASS=your-password
SMTP_FROM=noreply@chorus.com

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Worker Configuration
WORKER_CONCURRENCY=5
QUEUE_NAME=notifications
```

### Development

```bash
# Start in development mode with hot reload
npm run dev

# Build the project
npm run build

# Start in production mode
npm start

# Lint the code
npm run lint

# Format the code
npm run format
```

### Docker

Build and run with Docker:

```bash
# Build the image
docker build -t notification-worker .

# Run the container
docker run -d \
  --name notification-worker \
  --env-file .env \
  -p 9090:9090 \
  notification-worker
```

## Usage

The worker automatically processes jobs from the Redis queue. Jobs should be added to the queue with the following structure:

```typescript
interface NotificationJobData {
  type: 'email' | 'sms' | 'push';
  recipient: string;
  subject?: string;
  body: string;
  html?: string;
  data?: Record<string, any>;
}
```

### Example: Adding a job to the queue

```javascript
import { Queue } from 'bullmq';

const notificationQueue = new Queue('notifications', {
  connection: { host: 'localhost', port: 6379 }
});

// Email notification
await notificationQueue.add('email', {
  type: 'email',
  recipient: 'user@example.com',
  subject: 'Welcome to Chorus',
  body: 'Welcome to our platform!',
  html: '<h1>Welcome to our platform!</h1>'
});

// SMS notification
await notificationQueue.add('sms', {
  type: 'sms',
  recipient: '+1234567890',
  body: 'Your verification code is: 123456'
});
```

## Architecture

- **BullMQ**: Queue management and job processing
- **Nodemailer**: Email sending service
- **Twilio**: SMS sending service
- **Winston**: Logging
- **TypeScript**: Type safety and development experience

## Monitoring

The worker provides logging for:
- Job processing status
- Service connection health
- Error tracking
- Performance metrics

Logs are output in JSON format for easy integration with log aggregation tools.