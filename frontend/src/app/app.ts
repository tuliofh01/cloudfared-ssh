import { Component, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, TunnelStatus, SystemInfo } from './services/api.service';
import { FingerprintService, FingerprintData } from './services/fingerprint.service';
import { Subscription, interval } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
  // Signals for reactive state
  title = signal('Cloudfared Tunnel');
  
  // Tunnel status
  tunnelStatus = signal<TunnelStatus>({ status: 'unknown' });
  systemInfo = signal<SystemInfo | null>(null);
  
  // Logs
  logs = signal<string[]>([]);
  
  // Fingerprint
  fingerprint = signal<FingerprintData | null>(null);
  userIP = signal<string>('detecting...');
  showFingerprintPopup = signal(false);
  
  // Loading states
  isLoading = signal(true);
  isStarting = signal(false);
  isStopping = signal(false);
  
  // Computed values
  statusColor = computed(() => {
    const status = this.tunnelStatus().status;
    if (status === 'running') return 'online';
    if (status === 'starting' || status === 'crashed') return 'connecting';
    return 'offline';
  });
  
  statusText = computed(() => {
    const status = this.tunnelStatus().status;
    if (status === 'running') return 'ONLINE';
    if (status === 'starting') return 'CONNECTING';
    if (status === 'crashed') return 'CRASHED';
    return 'OFFLINE';
  });
  
  uptimeFormatted = computed(() => {
    const uptime = this.tunnelStatus().uptime || 0;
    if (uptime < 60) return `${uptime}s`;
    if (uptime < 3600) return `${Math.floor(uptime / 60)}m ${uptime % 60}s`;
    const hours = Math.floor(uptime / 3600);
    const minutes = Math.floor((uptime % 3600) / 60);
    return `${hours}h ${minutes}m`;
  });
  
  // Subscriptions
  private subscriptions: Subscription[] = [];
  
  constructor(
    private apiService: ApiService,
    private fingerprintService: FingerprintService
  ) {}
  
  async ngOnInit() {
    // Initialize fingerprint
    const fp = await this.fingerprintService.collectFingerprint();
    this.fingerprint.set(fp);
    
    const ip = await this.fingerprintService.getIPAddress();
    this.userIP.set(ip);
    
    // Poll for status and logs
    this.subscriptions.push(
      this.apiService.pollTunnelStatus(5000).subscribe({
        next: (status) => {
          this.tunnelStatus.set(status);
          this.isLoading.set(false);
        },
        error: () => {
          this.tunnelStatus.set({ status: 'unknown' });
          this.isLoading.set(false);
        }
      })
    );
    
    this.subscriptions.push(
      this.apiService.pollLogs(10000).subscribe({
        next: (data) => {
          this.logs.set(data.logs);
        }
      })
    );
  }
  
  ngOnDestroy() {
    this.subscriptions.forEach(sub => sub.unsubscribe());
  }
  
  startTunnel() {
    this.isStarting.set(true);
    this.tunnelStatus.set({ status: 'starting' });
    
    this.apiService.startTunnel().subscribe({
      next: () => {
        this.isStarting.set(false);
      },
      error: () => {
        this.isStarting.set(false);
        this.tunnelStatus.set({ status: 'stopped' });
      }
    });
  }
  
  stopTunnel() {
    this.isStopping.set(true);
    
    this.apiService.stopTunnel().subscribe({
      next: () => {
        this.isStopping.set(false);
        this.tunnelStatus.set({ status: 'stopped' });
      },
      error: () => {
        this.isStopping.set(false);
      }
    });
  }
  
  toggleFingerprintPopup() {
    this.showFingerprintPopup.update(v => !v);
  }
  
  formatUptime(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  }
  
  trackByFn(index: number, item: string): number {
    return index;
  }
}
