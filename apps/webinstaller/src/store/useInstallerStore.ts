import { create } from 'zustand';

interface CheckResult {
  status: boolean;
  message: string;
}

type CheckKey = 'api' | 'webdav' | 'ldap' | 'ldapAccess';

interface InstallerState {
  deploymentTarget: 'linuxmuster' | 'generic' | null;
  lmnExternalDomain: string;
  lmnBinduserDn: string;
  lmnBinduserPw: string;
  lmnLdapSchema: 'ldap' | 'ldaps';
  lmnLdapPort: number;
  edulutionExternalDomain: string;
  checks: Record<CheckKey, CheckResult | null>;
  initialAdminGroup: string;
  certificateConfigured: boolean;
  proxyDetected: boolean;

  setDeploymentTarget: (target: 'linuxmuster' | 'generic') => void;
  setTokenData: (data: { lmnExternalDomain: string; lmnBinduserDn: string; lmnBinduserPw: string }) => void;
  setConfiguration: (config: {
    lmnExternalDomain: string;
    lmnBinduserDn: string;
    lmnBinduserPw: string;
    lmnLdapSchema: 'ldap' | 'ldaps';
    lmnLdapPort: number;
    edulutionExternalDomain: string;
  }) => void;
  setCheckResult: (check: CheckKey, result: CheckResult) => void;
  resetChecks: () => void;
  setInitialAdminGroup: (group: string) => void;
  setCertificateConfigured: (value: boolean) => void;
  setProxyDetected: (value: boolean) => void;
  reset: () => void;
}

const initialState = {
  deploymentTarget: null as 'linuxmuster' | 'generic' | null,
  lmnExternalDomain: '',
  lmnBinduserDn: '',
  lmnBinduserPw: '',
  lmnLdapSchema: 'ldaps' as const,
  lmnLdapPort: 636,
  edulutionExternalDomain: '',
  checks: {
    api: null,
    webdav: null,
    ldap: null,
    ldapAccess: null,
  } as Record<CheckKey, CheckResult | null>,
  initialAdminGroup: '',
  certificateConfigured: false,
  proxyDetected: false,
};

const useInstallerStore = create<InstallerState>((set) => ({
  ...initialState,

  setDeploymentTarget: (target) => set({ deploymentTarget: target }),

  setTokenData: (data) =>
    set({
      lmnExternalDomain: data.lmnExternalDomain,
      lmnBinduserDn: data.lmnBinduserDn,
      lmnBinduserPw: data.lmnBinduserPw,
    }),

  setConfiguration: (config) => set(config),

  setCheckResult: (check, result) =>
    set((state) => ({
      checks: { ...state.checks, [check]: result },
    })),

  resetChecks: () =>
    set({
      checks: { api: null, webdav: null, ldap: null, ldapAccess: null },
    }),

  setInitialAdminGroup: (group) => set({ initialAdminGroup: group }),

  setCertificateConfigured: (value) => set({ certificateConfigured: value }),

  setProxyDetected: (value) => set({ proxyDetected: value }),

  reset: () => set(initialState),
}));

export default useInstallerStore;
