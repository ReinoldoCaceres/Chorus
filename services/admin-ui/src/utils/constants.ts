export const API_ENDPOINTS = {
  AGENTS: '/api/agents',
  CHATS: '/api/chats',
  ANALYTICS: '/api/analytics',
  NOTIFICATIONS: '/api/notifications',
  WEBSOCKET: '/ws',
} as const;

export const WEBSOCKET_EVENTS = {
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  AGENT_STATUS_CHANGE: 'agent_status_change',
  NEW_CHAT: 'new_chat',
  CHAT_UPDATE: 'chat_update',
  SYSTEM_ALERT: 'system_alert',
} as const;

export const AGENT_STATUS = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  BUSY: 'busy',
} as const;

export const NOTIFICATION_TYPES = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
} as const;