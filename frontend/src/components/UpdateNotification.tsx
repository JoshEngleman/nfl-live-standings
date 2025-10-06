import { useEffect, useState } from 'react';
import { Bell, X } from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';
import { UpdateResult } from '../types';

export function UpdateNotification() {
  const { lastMessage } = useWebSocket();
  const [notification, setNotification] = useState<UpdateResult | null>(null);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (lastMessage?.type === 'contest_update' && lastMessage.data) {
      setNotification(lastMessage.data);
      setShow(true);

      // Auto-hide after 5 seconds
      const timer = setTimeout(() => {
        setShow(false);
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [lastMessage]);

  if (!show || !notification) return null;

  return (
    <div className="fixed top-4 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-4 max-w-sm animate-slide-in">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-blue-600" />
          <h4 className="font-semibold text-gray-900">Contest Updated</h4>
        </div>
        <button
          onClick={() => setShow(false)}
          className="text-gray-400 hover:text-gray-600"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <p className="text-sm text-gray-600 mb-2">{notification.contest_id}</p>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-gray-500">Live Games:</span>
          <span className="ml-1 font-medium">{notification.live_games}</span>
        </div>
        <div>
          <span className="text-gray-500">Match Rate:</span>
          <span className="ml-1 font-medium">{notification.match_rate.toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-gray-500">Duration:</span>
          <span className="ml-1 font-medium">{notification.duration_seconds.toFixed(1)}s</span>
        </div>
        <div>
          <span className="text-gray-500">Lineups:</span>
          <span className="ml-1 font-medium">{notification.num_lineups}</span>
        </div>
      </div>
    </div>
  );
}
