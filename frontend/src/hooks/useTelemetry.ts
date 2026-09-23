import { useEffect, useState, useRef } from 'react';
import { TelemetryMessage } from '../types';

export function useTelemetry() {
  const [data, setData] = useState<TelemetryMessage | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimeout: any = null;
    let isMounted = true;

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/telemetry`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isMounted) setIsConnected(true);
        };

        ws.onmessage = (event) => {
          if (isMounted) {
            try {
              const parsed: TelemetryMessage = JSON.parse(event.data);
              setData(parsed);
            } catch (err) {
              console.error('Error parsing telemetry:', err);
            }
          }
        };

        ws.onclose = () => {
          if (isMounted) {
            setIsConnected(false);
            reconnectTimeout = setTimeout(connect, 2000);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (e) {
        if (isMounted) {
          reconnectTimeout = setTimeout(connect, 2000);
        }
      }
    }

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return { data, isConnected };
}
