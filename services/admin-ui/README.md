# Admin UI

A React-based admin dashboard for managing the Chorus platform.

## Features

- **Modern React**: Built with React 18+ and TypeScript
- **Responsive Design**: Tailwind CSS for modern, responsive UI
- **Real-time Updates**: WebSocket integration for live data
- **Agent Management**: Monitor and control AI agents
- **Chat Overview**: View and manage ongoing conversations
- **Analytics Dashboard**: Performance metrics and insights
- **Dark Mode Support**: Built-in dark/light theme switching

## Tech Stack

- **React 18+** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Router** for navigation
- **TanStack Query** for server state management
- **Socket.IO Client** for real-time communication
- **Axios** for HTTP requests

## Setup

### Prerequisites

- Node.js 18+
- NPM or Yarn

### Installation

```bash
npm install
```

### Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env.local
```

### Development

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npm run type-check
```

### Docker

```bash
# Build and run
docker build -t admin-ui .
docker run -d --name admin-ui -p 80:80 admin-ui
```