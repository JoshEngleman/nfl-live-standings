import { useEffect, useState } from 'react';
import { Target } from 'lucide-react';
import { UpdaterControl } from './components/UpdaterControl';
import { ContestList } from './components/ContestList';
import { WebSocketStatus } from './components/WebSocketStatus';
import { UpdateNotification } from './components/UpdateNotification';
import { LiveStatsTest } from './components/LiveStatsTest';
import { apiService } from './services/api';
import { HealthStatus } from './types';

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await apiService.getHealth();
        setHealth(data);
        setError(null);
      } catch (err) {
        setError('Cannot connect to backend server. Make sure it is running on http://localhost:8000');
        console.error(err);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <UpdateNotification />

      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <Target className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  NFL DFS Live Standings
                </h1>
                <p className="text-sm text-gray-500">
                  Real-time Monte Carlo simulation platform
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <LiveStatsTest />
              <WebSocketStatus />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
            <h3 className="text-red-800 font-semibold mb-2">Connection Error</h3>
            <p className="text-red-600 mb-4">{error}</p>
            <div className="bg-red-100 p-3 rounded text-sm text-red-800 font-mono">
              Make sure the backend is running:<br />
              <span className="text-red-900">cd backend && uvicorn main:app --reload</span>
            </div>
          </div>
        ) : (
          <>
            {health && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <div className="flex items-center gap-2 text-blue-800 mb-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span className="font-semibold">Backend Connected</span>
                  <span className="text-blue-600">•</span>
                  <span className="text-sm">Phase {health.status === 'healthy' ? '3' : '?'}</span>
                </div>
                <div className="grid grid-cols-5 gap-3 text-xs">
                  {Object.entries(health.components).map(([key, value]) => (
                    <div key={key} className="bg-white p-2 rounded">
                      <div className="text-gray-500 capitalize">
                        {key.replace(/_/g, ' ')}
                      </div>
                      <div className={`font-semibold ${value === 'ok' || value === 'running' ? 'text-green-600' : 'text-gray-600'}`}>
                        {value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
              <div className="lg:col-span-1">
                <UpdaterControl />
              </div>
              <div className="lg:col-span-2">
                <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4">Quick Start</h2>
                  <div className="space-y-3 text-sm text-gray-600">
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-semibold">
                        1
                      </div>
                      <div>
                        <strong className="text-gray-900">Load Contest Data</strong>
                        <p>Run demo scripts to add sample contests or use the Python API</p>
                        <code className="block mt-1 bg-gray-100 px-2 py-1 rounded text-xs font-mono">
                          python examples/demo_automation.py
                        </code>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-semibold">
                        2
                      </div>
                      <div>
                        <strong className="text-gray-900">Start Background Updater</strong>
                        <p>Click "Start Updater" to enable automatic updates every 2 minutes</p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-semibold">
                        3
                      </div>
                      <div>
                        <strong className="text-gray-900">Monitor Live Updates</strong>
                        <p>Watch real-time updates appear automatically via WebSocket</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <ContestList />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-500">
            <p>141,000+ iterations/second • 95%+ name matching • Real-time ESPN stats</p>
            <p className="mt-1">Built with ⚡ and 🏈 for DFS</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
