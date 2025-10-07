import { useEffect, useState } from 'react';
import { Settings as SettingsIcon, X, RotateCcw } from 'lucide-react';
import { apiService } from '../services/api';

export function Settings() {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [usePositionBased, setUsePositionBased] = useState(false);
  const [iterations, setIterations] = useState(10000);
  const [useLognormal, setUseLognormal] = useState(true);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await apiService.getSettings();
      if (response.settings) {
        setUsePositionBased(response.settings.use_position_based);
        setIterations(response.settings.iterations);
        setUseLognormal(response.settings.use_lognormal);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await apiService.updateSettings({
        use_position_based: usePositionBased,
        iterations: iterations,
        use_lognormal: useLognormal
      });
      setIsOpen(false);
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset all settings to defaults?')) return;

    setLoading(true);
    try {
      const response = await apiService.resetSettings();
      if (response.settings) {
        setUsePositionBased(response.settings.use_position_based);
        setIterations(response.settings.iterations);
        setUseLognormal(response.settings.use_lognormal);
      }
    } catch (error) {
      console.error('Failed to reset settings:', error);
      alert('Failed to reset settings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Settings Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        title="Simulation Settings"
      >
        <SettingsIcon className="w-5 h-5 text-gray-600" />
        <span className="text-sm font-medium text-gray-700">Settings</span>
      </button>

      {/* Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                  <SettingsIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">Simulation Settings</h2>
                  <p className="text-sm text-gray-500">Configure Monte Carlo simulation parameters</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Position-Based Simulation Toggle */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <div className="relative">
                        <input
                          type="checkbox"
                          checked={usePositionBased}
                          onChange={(e) => setUsePositionBased(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-300 rounded-full peer peer-checked:bg-blue-600 peer-focus:ring-4 peer-focus:ring-blue-300 transition-all"></div>
                        <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-all peer-checked:translate-x-5"></div>
                      </div>
                      <div>
                        <div className="font-semibold text-gray-900">Position-Based Simulation</div>
                        <div className="text-sm text-gray-600 mt-1">
                          Component-based modeling that captures discrete TDs, boom/bust patterns, and position-specific volatility
                        </div>
                      </div>
                    </label>
                  </div>
                </div>

                {usePositionBased && (
                  <div className="mt-3 pl-14 text-sm text-blue-800 bg-blue-100 p-3 rounded">
                    <div className="font-medium mb-1">📊 Position-Based Features:</div>
                    <ul className="list-disc list-inside space-y-1">
                      <li>Discrete TD events (Poisson) with realistic 4/6-pt steps</li>
                      <li>Continuous yards (Normal/Gamma) with position-specific variance</li>
                      <li>WR boom/bust overlay (+35% volatility)</li>
                      <li>Kicker FG/XP discrete scoring structure</li>
                      <li>~34% higher variance vs log-normal</li>
                    </ul>
                  </div>
                )}
              </div>

              {/* Iterations Slider */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="font-semibold text-gray-900">
                    Monte Carlo Iterations
                  </label>
                  <span className="text-2xl font-bold text-blue-600">
                    {iterations.toLocaleString()}
                  </span>
                </div>
                <input
                  type="range"
                  min="1000"
                  max="50000"
                  step="1000"
                  value={iterations}
                  onChange={(e) => setIterations(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1,000</span>
                  <span>25,000</span>
                  <span>50,000</span>
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  Higher iterations = more accurate probabilities but slower simulations.
                  {iterations >= 20000 && ' ⚠️ High iteration count may slow down updates.'}
                </p>
              </div>

              {/* Log-Normal Toggle (only shown when position-based is OFF) */}
              {!usePositionBased && (
                <div className="border border-gray-200 rounded-lg p-4">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <div className="relative">
                      <input
                        type="checkbox"
                        checked={useLognormal}
                        onChange={(e) => setUseLognormal(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-300 rounded-full peer peer-checked:bg-blue-600 peer-focus:ring-4 peer-focus:ring-blue-300 transition-all"></div>
                      <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-all peer-checked:translate-x-5"></div>
                    </div>
                    <div>
                      <div className="font-semibold text-gray-900">Use Log-Normal Distribution</div>
                      <div className="text-sm text-gray-600 mt-1">
                        Right-skewed distribution for volatility modeling (vs Normal distribution)
                      </div>
                    </div>
                  </label>
                </div>
              )}

              {/* Info Box */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="font-semibold text-gray-900 mb-2">ℹ️ How Settings Work</div>
                <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
                  <li>Settings apply to <strong>all future simulations</strong></li>
                  <li>Changes take effect on the next update or manual trigger</li>
                  <li>Position-based simulation is ~5-10x slower but more accurate</li>
                  <li>Default: 10,000 iterations with log-normal distribution</li>
                </ul>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
              <button
                onClick={handleReset}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
              >
                <RotateCcw className="w-4 h-4" />
                Reset to Defaults
              </button>
              <div className="flex gap-3">
                <button
                  onClick={() => setIsOpen(false)}
                  disabled={loading}
                  className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={loading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
