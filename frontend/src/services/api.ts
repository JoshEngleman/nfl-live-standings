import { Contest, UpdaterStatus, HealthStatus, UpdateResult } from '../types';

const API_BASE_URL = 'http://localhost:8001';

class APIService {
  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    // Create an AbortController for timeout
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      return response.json();
    } catch (error: any) {
      if (error.name === 'AbortError') {
        throw new Error('Request timed out after 30 seconds');
      }
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  // Health check
  async getHealth(): Promise<HealthStatus> {
    return this.fetch<HealthStatus>('/health');
  }

  // Contest endpoints
  async getContests(): Promise<{ total: number; active: number; contests: Contest[] }> {
    return this.fetch('/api/contests');
  }

  async getContest(contestId: string): Promise<Contest> {
    return this.fetch(`/api/contests/${contestId}`);
  }

  async getContestLineups(contestId: string, limit: number = 50, offset: number = 0, sortBy: string = 'rank', username?: string): Promise<any> {
    let url = `/api/contests/${contestId}/lineups?limit=${limit}&offset=${offset}&sort_by=${sortBy}`;
    if (username && username.trim()) {
      url += `&username=${encodeURIComponent(username.trim())}`;
    }
    return this.fetch(url);
  }

  async deactivateContest(contestId: string): Promise<{ status: string; message: string }> {
    return this.fetch(`/api/contests/${contestId}/deactivate`, {
      method: 'POST',
    });
  }

  async removeContest(contestId: string): Promise<{ status: string; message: string }> {
    return this.fetch(`/api/contests/${contestId}`, {
      method: 'DELETE',
    });
  }

  // Updater control
  async getUpdaterStatus(): Promise<UpdaterStatus> {
    return this.fetch('/api/updater/status');
  }

  async startUpdater(): Promise<any> {
    return this.fetch('/api/updater/control', {
      method: 'POST',
      body: JSON.stringify({ action: 'start' }),
    });
  }

  async stopUpdater(): Promise<any> {
    return this.fetch('/api/updater/control', {
      method: 'POST',
      body: JSON.stringify({ action: 'stop' }),
    });
  }

  async triggerManualUpdate(): Promise<{ status: string; message: string; results: Record<string, UpdateResult> }> {
    return this.fetch('/api/updater/trigger', {
      method: 'POST',
    });
  }

  async testLiveStats(): Promise<any> {
    return this.fetch('/api/test-live-stats');
  }

  async getOptimalLineup(contestId: string): Promise<any> {
    return this.fetch(`/api/contests/${contestId}/optimal-lineup`);
  }

  async getPlayersPerformance(contestId: string, sortBy: string = 'score'): Promise<any> {
    return this.fetch(`/api/contests/${contestId}/players?sort_by=${sortBy}`);
  }

  // Replay control
  async fetchHistoricalGame(gameId: string, season: number, week: number): Promise<any> {
    return this.fetch('/api/test/replay/fetch-game', {
      method: 'POST',
      body: JSON.stringify({ game_id: gameId, season, week }),
    });
  }

  async loadGameForReplay(gameId: string): Promise<any> {
    return this.fetch(`/api/test/replay/load/${gameId}`, {
      method: 'POST',
    });
  }

  async advanceReplayQuarter(): Promise<any> {
    return this.fetch('/api/test/replay/advance', {
      method: 'POST',
    });
  }

  async resetReplay(): Promise<any> {
    return this.fetch('/api/test/replay/reset', {
      method: 'POST',
    });
  }

  async getReplayStatus(): Promise<any> {
    return this.fetch('/api/test/replay/status');
  }

  // Payout structure
  async updatePayoutStructure(contestId: string, payoutText: string, entryFee?: number): Promise<any> {
    return this.fetch(`/api/contests/${contestId}/payout-structure`, {
      method: 'POST',
      body: JSON.stringify({
        payout_text: payoutText,
        entry_fee: entryFee
      }),
    });
  }

  // Settings
  async getSettings(): Promise<any> {
    return this.fetch('/api/settings');
  }

  async updateSettings(settings: { use_position_based?: boolean; iterations?: number; use_lognormal?: boolean }): Promise<any> {
    return this.fetch('/api/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  }

  async resetSettings(): Promise<any> {
    return this.fetch('/api/settings/reset', {
      method: 'POST',
    });
  }
}

export const apiService = new APIService();
