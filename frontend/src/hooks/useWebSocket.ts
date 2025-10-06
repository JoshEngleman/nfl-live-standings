import { useEffect, useState } from 'react';
import { wsService } from '../services/websocket';
import { WebSocketMessage } from '../types';

export function useWebSocket() {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  useEffect(() => {
    const handleMessage = (message: WebSocketMessage) => {
      setLastMessage(message);

      if (message.type === 'connection_established') {
        setIsConnected(true);
      }
    };

    wsService.addMessageHandler(handleMessage);
    wsService.connect();

    // Check connection status periodically
    const interval = setInterval(() => {
      setIsConnected(wsService.isConnected());
    }, 1000);

    return () => {
      wsService.removeMessageHandler(handleMessage);
      clearInterval(interval);
      wsService.disconnect();
    };
  }, []);

  return {
    isConnected,
    lastMessage,
    send: wsService.send.bind(wsService),
    requestStatus: wsService.requestStatus.bind(wsService),
  };
}
