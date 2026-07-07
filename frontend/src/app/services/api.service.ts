import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, interval, switchMap, startWith } from 'rxjs';

export interface TunnelStatus {
  status: string;
  pid?: number;
  uptime?: number;
  url?: string;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  userId?: string;
  ip?: string;
}

export interface SystemInfo {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  uptime: number;
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  // Note: In production, this would point to your Cloudflare Worker URL
  // For local development, it would be http://localhost:5000
  private baseUrl = ''; // Will be set dynamically based on environment

  constructor(private http: HttpClient) {
    // Detect if we're running locally or in production
    if (typeof window !== 'undefined') {
      if (window.location.hostname === 'localhost') {
        this.baseUrl = 'http://localhost:5000';
      }
      // In production on Cloudflare, API calls would go to relative paths
    }
  }

  getTunnelStatus(): Observable<TunnelStatus> {
    return this.http.get<TunnelStatus>(`${this.baseUrl}/api/tunnel/status`);
  }

  startTunnel(service: string = 'ssh://localhost:22'): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/tunnel/start`, { service });
  }

  stopTunnel(): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/tunnel/stop`, {});
  }

  getLogs(lines: number = 100): Observable<{ logs: string[]; count: number }> {
    return this.http.get<{ logs: string[]; count: number }>(`${this.baseUrl}/api/logs?lines=${lines}`);
  }

  getSystemInfo(): Observable<SystemInfo> {
    return this.http.get<SystemInfo>(`${this.baseUrl}/api/system/info`);
  }

  // Polling methods for real-time updates
  pollTunnelStatus(intervalMs: number = 5000): Observable<TunnelStatus> {
    return interval(intervalMs).pipe(
      startWith(0),
      switchMap(() => this.getTunnelStatus())
    );
  }

  pollLogs(intervalMs: number = 10000): Observable<{ logs: string[]; count: number }> {
    return interval(intervalMs).pipe(
      startWith(0),
      switchMap(() => this.getLogs(50))
    );
  }
}
