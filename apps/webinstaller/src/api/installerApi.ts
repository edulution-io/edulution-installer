import type { DeploymentTarget, OrganizationType } from '@shared-types';

interface StatusResponse {
  status: boolean;
  message: string;
}

interface ConfigurationRequest {
  organizationType: OrganizationType;
  deploymentTarget: DeploymentTarget;
  lmnExternalDomain: string;
  lmnBinduserDn: string;
  lmnBinduserPw: string;
  lmnLdapSchema: 'ldap' | 'ldaps';
  lmnLdapPort: number;
  edulutionExternalDomain: string;
}

interface SsCertificateRequest {
  countrycode: string;
  state: string;
  city: string;
  organization: string;
  valid_days: number;
}

interface LeCertificateRequest {
  email: string;
  dns_provider: string;
}

export interface AcmeDnsRegistration {
  username: string;
  password: string;
  fulldomain: string;
  subdomain: string;
  allowfrom: string[];
}

interface LeCertificateResponse extends StatusResponse {
  registration?: AcmeDnsRegistration;
}

const apiFetch = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json() as Promise<T>;
};

export const checkToken = (token: string): Promise<boolean> =>
  apiFetch<boolean>('/api/check-token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });

export const submitConfiguration = (config: ConfigurationRequest): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/configure', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

export const checkApiStatus = (): Promise<StatusResponse> => apiFetch<StatusResponse>('/api/check-api-status');

export const checkWebDavStatus = (): Promise<StatusResponse> => apiFetch<StatusResponse>('/api/check-webdav-status');

export const checkLdapStatus = (): Promise<StatusResponse> => apiFetch<StatusResponse>('/api/check-ldap-status');

export const checkLdapAccessStatus = (): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/check-ldap-access-status');

export const submitAdminGroup = (adminGroup: string): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/set-admin-group', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ admin_group: adminGroup }),
  });

export const createSsCertificate = (data: SsCertificateRequest): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/create-ss-certificate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const createLeCertificate = (data: LeCertificateRequest): Promise<LeCertificateResponse> =>
  apiFetch<LeCertificateResponse>('/api/create-le-certificate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const uploadCertificate = (certFile: File, keyFile: File): Promise<StatusResponse> => {
  const formData = new FormData();
  formData.append('cert', certFile);
  formData.append('key', keyFile);
  return apiFetch<StatusResponse>('/api/upload-certificate', {
    method: 'POST',
    body: formData,
  });
};

export const startInstallation = (): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/finish', { method: 'POST' });

export const checkProxy = (): Promise<{ proxyDetected: boolean }> =>
  apiFetch<{ proxyDetected: boolean }>('/api/proxy-check');

// --- LMN Installer API ---

interface SSHConnection {
  host: string;
  port: number;
  user: string;
  password: string;
}

interface RequirementCheck {
  name: string;
  status: 'passed' | 'failed' | 'skipped';
  required: string | null;
  actual: string | null;
  message: string;
}

interface DiskInfo {
  name: string;
  size_gb: number;
}

interface SystemInfo {
  os: string | null;
  os_version: string | null;
  ram_gb: number | null;
  disks: DiskInfo[];
}

export interface RequirementsResponse {
  playbook: string;
  all_passed: boolean;
  checks: RequirementCheck[];
  system_info: SystemInfo;
}

interface PlaybookStartResponse {
  job_id: string;
  status: string;
  message: string;
}

export const bootstrapLmnServer = async (
  ssh: SSHConnection,
  onMessage: (line: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
): Promise<() => void> => {
  // 1. Start bootstrap via POST
  try {
    const response = await fetch('/api/lmn/bootstrap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ssh),
    });
    if (!response.ok) {
      onError('Failed to start bootstrap');
      return () => {};
    }
  } catch {
    onError('Network error');
    return () => {};
  }

  // 2. Connect to SSE stream (browser auto-reconnects with Last-Event-ID)
  const es = new EventSource('/api/lmn/bootstrap/stream');

  es.onmessage = (event: MessageEvent<string>) => {
    onMessage(event.data);
  };

  es.addEventListener('done', () => {
    es.close();
    onDone();
  });

  es.addEventListener('failed', (event: MessageEvent<string>) => {
    es.close();
    onError(event.data || 'Bootstrap failed');
  });

  es.onerror = () => {
    // readyState CONNECTING = browser is auto-reconnecting (normal)
    // readyState CLOSED = server rejected or permanent failure
    if (es.readyState === EventSource.CLOSED) {
      onError('Connection lost');
    }
  };

  return () => es.close();
};

export const getLmnHealth = (): Promise<StatusResponse> => apiFetch<StatusResponse>('/api/lmn/health');

export const checkLmnConnection = (host: string): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/lmn/check-connection', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ host }),
  });

export const checkLmnRequirements = (playbook: string): Promise<RequirementsResponse> =>
  apiFetch<RequirementsResponse>(`/api/lmn/playbook/${playbook}/requirements`);

export const startLmnPlaybook = (
  playbook: string,
  extraVars: Record<string, unknown> = {},
): Promise<PlaybookStartResponse> =>
  apiFetch<PlaybookStartResponse>(`/api/lmn/playbook/${playbook}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ variables: { extra_vars: extraVars } }),
  });

export const createLmnWebSocket = (): WebSocket => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return new WebSocket(`${protocol}//${window.location.host}/ws/lmn/output`);
};

export interface EdulutionConfig {
  binduser_dn: string;
  binduser_password: string;
}

export const getEdulutionConfig = (): Promise<EdulutionConfig> =>
  apiFetch<EdulutionConfig>('/api/lmn/edulution-config');

export const shutdownLmnInstaller = (): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/lmn/shutdown', { method: 'POST' });

export const shutdownInstaller = (): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/shutdown', { method: 'POST' });
