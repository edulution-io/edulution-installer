interface StatusResponse {
  status: boolean;
  message: string;
}

interface ConfigurationRequest {
  deploymentTarget: 'linuxmuster' | 'generic';
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
  organisation: string;
  valid_days: number;
}

interface LeCertificateRequest {
  email: string;
}

const apiFetch = async <T>(url: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(url, options);
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

export const createLeCertificate = (data: LeCertificateRequest): Promise<StatusResponse> =>
  apiFetch<StatusResponse>('/api/create-le-certificate', {
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
