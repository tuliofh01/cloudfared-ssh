import { Injectable } from '@angular/core';

export interface FingerprintData {
  hash: string;
  canvas: string;
  audio: string;
  screen: string;
  timezone: string;
  language: string;
  platform: string;
  hardwareConcurrency: number;
  colorDepth: number;
}

@Injectable({
  providedIn: 'root'
})
export class FingerprintService {
  private fingerprintHash: string = '';
  private fingerprintData: FingerprintData | null = null;

  constructor() {
    this.collectFingerprint();
  }

  async collectFingerprint(): Promise<FingerprintData> {
    const data: FingerprintData = {
      hash: '',
      canvas: await this.getCanvasFingerprint(),
      audio: await this.getAudioFingerprint(),
      screen: `${screen.width}x${screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      language: navigator.language,
      platform: navigator.platform,
      hardwareConcurrency: navigator.hardwareConcurrency || 0,
      colorDepth: screen.colorDepth
    };

    // Generate hash from collected data
    data.hash = await this.hashData(JSON.stringify(data));
    this.fingerprintHash = data.hash;
    this.fingerprintData = data;

    return data;
  }

  private async getCanvasFingerprint(): Promise<string> {
    try {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return '';

      canvas.width = 200;
      canvas.height = 50;

      // Draw various elements to create a unique fingerprint
      ctx.textBaseline = 'top';
      ctx.font = '14px Arial';
      ctx.fillStyle = '#f60';
      ctx.fillRect(125, 1, 62, 20);
      ctx.fillStyle = '#069';
      ctx.fillText('Cloudfared', 2, 15);
      ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
      ctx.fillText('Tunnel', 4, 17);

      // Get the data URL and hash it
      const dataUrl = canvas.toDataURL();
      return await this.hashData(dataUrl);
    } catch {
      return '';
    }
  }

  private async getAudioFingerprint(): Promise<string> {
    try {
      // Audio context fingerprinting
      const audioContext = new AudioContext();
      const oscillator = audioContext.createOscillator();
      const analyser = audioContext.createAnalyser();
      const gain = audioContext.createGain();
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      gain.gain.value = 0;
      oscillator.type = 'triangle';
      oscillator.frequency.value = 10000;

      oscillator.connect(analyser);
      analyser.connect(processor);
      processor.connect(gain);
      gain.connect(audioContext.destination);

      oscillator.start(0);

      // Create a simple fingerprint based on audio context properties
      const hasMediaDevices = typeof navigator.mediaDevices?.getUserMedia === 'function';
      const fingerprint = `${audioContext.sampleRate}-${audioContext.state}-${hasMediaDevices ? 'available' : 'unavailable'}`;
      
      oscillator.stop();
      audioContext.close();

      return await this.hashData(fingerprint);
    } catch {
      return '';
    }
  }

  private async hashData(data: string): Promise<string> {
    try {
      const encoder = new TextEncoder();
      const dataBuffer = encoder.encode(data);
      const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch {
      // Fallback for environments without crypto.subtle
      let hash = 0;
      for (let i = 0; i < data.length; i++) {
        const char = data.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
      }
      return hash.toString(16);
    }
  }

  getHash(): string {
    return this.fingerprintHash;
  }

  getFingerprintData(): FingerprintData | null {
    return this.fingerprintData;
  }

  async getIPAddress(): Promise<string> {
    try {
      // Using a simple IP detection endpoint
      const response = await fetch('https://api.ipify.org?format=json');
      const data = await response.json();
      return data.ip;
    } catch {
      return 'unknown';
    }
  }
}
