import { useState, useEffect } from 'react';
import { Play, Square, RefreshCw, Activity } from 'lucide-react';
import { apiService } from '../services/api';
import { UpdaterStatus } from '../types';

export function UpdaterControl() {
  const [status, setStatus] = useState<UpdaterStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await apiService.getUpdaterStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch updater status');
      console.error(err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setLoading(true);
    try {
      await apiService.startUpdater();
      await fetchStatus();
      setError(null);
    } catch (err) {
      setError('Failed to start updater');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await apiService.stopUpdater();
      await fetchStatus();
      setError(null);
    } catch (err) {
      setError('Failed to stop updater');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleTrigger = async () => {
    setLoading(true);
    try {
      await apiService.triggerManualUpdate();
      setError(null);
    } catch (err) {
      setError('Failed to trigger update');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (!status) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Background Updater
        </h2>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${status.is_running ? 'bg-green-500' : 'bg-gray-400'}`}></div>
          <span className="text-sm font-medium text-gray-700">
            {status.is_running ? 'Running' : 'Stopped'}
          </span>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-sm text-gray-600">Update Interval</div>
          <div className="text-lg font-semibold text-gray-900">
            {status.update_interval_seconds}s
          </div>
        </div>
        <div className="bg-gray-50 p-3 rounded">
          <div className="text-sm text-gray-600">Active Contests</div>
          <div className="text-lg font-semibold text-gray-900">
            {status.active_contests}
          </div>
        </div>
      </div>

      {status.next_run && (
        <div className="mb-4 text-sm text-gray-600">
          Next update: {new Date(status.next_run).toLocaleTimeString()}
        </div>
      )}

      <div className="flex gap-2">
        {!status.is_running ? (
          <button
            onClick={handleStart}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <Play className="w-4 h-4" />
            Start Updater
          </button>
        ) : (
          <button
            onClick={handleStop}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <Square className="w-4 h-4" />
            Stop Updater
          </button>
        )}

        <button
          onClick={handleTrigger}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Trigger Now
        </button>
      </div>
    </div>
  );
}
