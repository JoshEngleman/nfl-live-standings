import { Contest, UpdaterStatus, HealthStatus, UpdateResult } from '../types';

const API_BASE_URL = 'http://localhost:8001';

class APIService {
  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
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
}

export const apiService = new APIService();
