import { create } from 'zustand';
import type { DeploymentTarget, OrganizationType } from '@shared-types';

interface CheckResult {
  status: boolean;
  message: string;
}

type CheckKey = 'api' | 'webdav' | 'ldap' | 'ldapAccess';

type LmnStatus = 'idle' | 'running' | 'completed' | 'failed';

interface LogEntry {
  id: number;
  text: string;
}
type AdType = 'existing' | 'new';

interface InstallerState {
  organizationType: OrganizationType | null;
  adType: AdType | null;
  deploymentTarget: DeploymentTarget | null;
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

  lmnSshHost: string;
  lmnSshPort: number;
  lmnSshUser: string;
  lmnSshPassword: string;
  lmnBootstrapStatus: LmnStatus;
  lmnPlaybookStatus: LmnStatus;
  lmnOutputLog: LogEntry[];
  lmnRequirementsPassed: boolean;

  lmnServerIp: string;
  lmnNetmask: string;
  lmnGateway: string;
  lmnServername: string;
  lmnDomainname: string;
  lmnSchoolname: string;
  lmnLocation: string;
  lmnCountry: string;
  lmnState: string;
  lmnDhcprange: string;
  lmnAdminpw: string;
  lmnTimezone: string;
  lmnLocale: string;

  setOrganizationType: (type: OrganizationType) => void;
  setAdType: (type: AdType) => void;
  setDeploymentTarget: (target: DeploymentTarget) => void;
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
  setLmnSsh: (ssh: { host: string; port: number; user: string; password: string }) => void;
  setLmnBootstrapStatus: (status: LmnStatus) => void;
  setLmnPlaybookStatus: (status: LmnStatus) => void;
  appendLmnOutput: (line: string) => void;
  clearLmnOutput: () => void;
  setLmnRequirementsPassed: (value: boolean) => void;
  setLmnConfig: (config: {
    lmnServerIp: string;
    lmnNetmask: string;
    lmnGateway: string;
    lmnServername: string;
    lmnDomainname: string;
    lmnSchoolname: string;
    lmnLocation: string;
    lmnCountry: string;
    lmnState: string;
    lmnDhcprange: string;
    lmnAdminpw: string;
    lmnTimezone: string;
    lmnLocale: string;
  }) => void;
  reset: () => void;
}

const initialState = {
  organizationType: null as OrganizationType | null,
  adType: null as AdType | null,
  deploymentTarget: null as DeploymentTarget | null,
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
  lmnSshHost: '',
  lmnSshPort: 22,
  lmnSshUser: 'root',
  lmnSshPassword: '',
  lmnBootstrapStatus: 'idle' as LmnStatus,
  lmnPlaybookStatus: 'idle' as LmnStatus,
  lmnOutputLog: [] as LogEntry[],
  lmnRequirementsPassed: false,
  lmnServerIp: '10.0.0.1',
  lmnNetmask: '255.255.0.0',
  lmnGateway: '10.0.0.254',
  lmnServername: 'server',
  lmnDomainname: 'linuxmuster.lan',
  lmnSchoolname: 'Meine Schule',
  lmnLocation: 'Musterstadt',
  lmnCountry: 'de',
  lmnState: 'BW',
  lmnDhcprange: '10.0.100.1 10.0.100.254',
  lmnAdminpw: '',
  lmnTimezone: 'Europe/Berlin',
  lmnLocale: 'de_DE.UTF-8',
};

let logIdCounter = 0;

const useInstallerStore = create<InstallerState>((set) => ({
  ...initialState,

  setOrganizationType: (type) => set({ organizationType: type }),

  setAdType: (type) => set({ adType: type }),

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

  setLmnSsh: (ssh) =>
    set({
      lmnSshHost: ssh.host,
      lmnSshPort: ssh.port,
      lmnSshUser: ssh.user,
      lmnSshPassword: ssh.password,
    }),

  setLmnBootstrapStatus: (status) => set({ lmnBootstrapStatus: status }),

  setLmnPlaybookStatus: (status) => set({ lmnPlaybookStatus: status }),

  appendLmnOutput: (line) =>
    set((state) => {
      const id = logIdCounter;
      logIdCounter += 1;
      return { lmnOutputLog: [...state.lmnOutputLog, { id, text: line }] };
    }),

  clearLmnOutput: () => {
    logIdCounter = 0;
    set({ lmnOutputLog: [] });
  },

  setLmnRequirementsPassed: (value) => set({ lmnRequirementsPassed: value }),

  setLmnConfig: (config) => set(config),

  reset: () => set(initialState),
}));

export default useInstallerStore;
