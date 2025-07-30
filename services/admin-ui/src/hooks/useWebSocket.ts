import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';

interface UseWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  reconnection?: boolean;
  reconnectionAttempts?: number;
  reconnectionDelay?: number;
}

interface WebSocketState {
  socket: Socket | null;
  isConnected: boolean;
  connectionError: string | null;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    url = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:3001',
    autoConnect = true,
    reconnection = true,
    reconnectionAttempts = 5,
    reconnectionDelay = 1000,
  } = options;

  const [state, setState] = useState<WebSocketState>({
    socket: null,
    isConnected: false,
    connectionError: null,
  });

  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    if (!autoConnect) return;

    const socket = io(url, {
      reconnection,
      reconnectionAttempts,
      reconnectionDelay,
      timeout: 5000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setState((prev) => ({
        ...prev,
        isConnected: true,
        connectionError: null,
      }));
    });

    socket.on('disconnect', () => {
      setState((prev) => ({
        ...prev,
        isConnected: false,
      }));
    });

    socket.on('connect_error', (error) => {
      setState((prev) => ({
        ...prev,
        connectionError: error.message,
        isConnected: false,
      }));
    });

    setState((prev) => ({
      ...prev,
      socket,
    }));

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [url, autoConnect, reconnection, reconnectionAttempts, reconnectionDelay]);

  const connect = () => {
    if (socketRef.current && !socketRef.current.connected) {
      socketRef.current.connect();
    }
  };

  const disconnect = () => {
    if (socketRef.current) {
      socketRef.current.disconnect();
    }
  };

  const emit = (event: string, data?: any) => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit(event, data);
    }
  };

  const on = (event: string, callback: (...args: any[]) => void) => {
    if (socketRef.current) {
      socketRef.current.on(event, callback);
    }
  };

  const off = (event: string, callback?: (...args: any[]) => void) => {
    if (socketRef.current) {
      socketRef.current.off(event, callback);
    }
  };

  return {
    ...state,
    connect,
    disconnect,
    emit,
    on,
    off,
  };
};