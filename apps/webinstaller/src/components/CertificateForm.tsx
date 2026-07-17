import { useState, useCallback, useRef, useEffect, Fragment } from 'react';
import { useTranslation } from 'react-i18next';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner, faCircleCheck, faCircleXmark } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@edulution-io/ui-kit';
import { Input } from '@shared-ui';
import useInstallerStore from '../store/useInstallerStore';
import { createSsCertificate, createLeCertificate, testLeCertificate, uploadCertificate } from '../api/installerApi';

type CertType = 'self-signed' | 'letsencrypt' | 'upload';
type OperationStatus = 'idle' | 'loading' | 'success' | 'error';

interface AcmeDnsRegistration {
  username: string;
  password: string;
  fulldomain: string;
  subdomain: string;
  allowfrom: string[];
}

type LeKind = 'http' | 'acme-dns' | 'dns';

interface LeCredentialField {
  env: string;
  label: string;
  secret?: boolean;
  optional?: boolean;
}

interface LeMethod {
  id: string;
  label: string;
  kind: LeKind;
  fields?: LeCredentialField[];
}

// Kuratierte Let's-Encrypt-Methoden. Provider-Codes und ENV-Namen entsprechen
// exakt Traefik/lego. "netzint" nutzt acme-dns mit dynamischer Registrierung.
const LE_METHODS: LeMethod[] = [
  { id: 'http', label: 'HTTP-Challenge (Port 80, kein Wildcard)', kind: 'http' },
  { id: 'netzint', label: 'DNS · acme-dns (Netzint)', kind: 'acme-dns' },
  {
    id: 'cloudflare',
    label: 'DNS · Cloudflare',
    kind: 'dns',
    fields: [{ env: 'CF_DNS_API_TOKEN', label: 'API-Token', secret: true }],
  },
  {
    id: 'hetzner',
    label: 'DNS · Hetzner',
    kind: 'dns',
    fields: [{ env: 'HETZNER_API_TOKEN', label: 'API-Token', secret: true }],
  },
  {
    id: 'ionos',
    label: 'DNS · IONOS',
    kind: 'dns',
    fields: [{ env: 'IONOS_API_KEY', label: 'API-Key (prefix.secret)', secret: true }],
  },
  {
    id: 'netcup',
    label: 'DNS · netcup',
    kind: 'dns',
    fields: [
      { env: 'NETCUP_CUSTOMER_NUMBER', label: 'Kundennummer' },
      { env: 'NETCUP_API_KEY', label: 'API-Key', secret: true },
      { env: 'NETCUP_API_PASSWORD', label: 'API-Passwort', secret: true },
    ],
  },
  {
    id: 'inwx',
    label: 'DNS · INWX',
    kind: 'dns',
    fields: [
      { env: 'INWX_USERNAME', label: 'Benutzername' },
      { env: 'INWX_PASSWORD', label: 'Passwort', secret: true },
    ],
  },
  {
    id: 'desec',
    label: 'DNS · deSEC',
    kind: 'dns',
    fields: [{ env: 'DESEC_TOKEN', label: 'Token', secret: true }],
  },
  {
    id: 'digitalocean',
    label: 'DNS · DigitalOcean',
    kind: 'dns',
    fields: [{ env: 'DO_AUTH_TOKEN', label: 'API-Token', secret: true }],
  },
  {
    id: 'gandiv5',
    label: 'DNS · Gandi',
    kind: 'dns',
    fields: [{ env: 'GANDIV5_PERSONAL_ACCESS_TOKEN', label: 'Personal Access Token', secret: true }],
  },
  {
    id: 'ovh',
    label: 'DNS · OVH',
    kind: 'dns',
    fields: [
      { env: 'OVH_ENDPOINT', label: 'Endpoint (z.B. ovh-eu)' },
      { env: 'OVH_APPLICATION_KEY', label: 'Application Key' },
      { env: 'OVH_APPLICATION_SECRET', label: 'Application Secret', secret: true },
      { env: 'OVH_CONSUMER_KEY', label: 'Consumer Key', secret: true },
    ],
  },
  {
    id: 'route53',
    label: 'DNS · AWS Route53',
    kind: 'dns',
    fields: [
      { env: 'AWS_ACCESS_KEY_ID', label: 'Access Key ID' },
      { env: 'AWS_SECRET_ACCESS_KEY', label: 'Secret Access Key', secret: true },
      { env: 'AWS_REGION', label: 'Region (z.B. eu-central-1)', optional: true },
    ],
  },
];

const CertificateForm = () => {
  const { t } = useTranslation();
  const { edulutionExternalDomain, setCertificateConfigured } = useInstallerStore();

  const [certType, setCertType] = useState<CertType>('upload');
  const [status, setStatus] = useState<OperationStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  // Self-signed fields
  const [countryCode, setCountryCode] = useState('');
  const [state, setState] = useState('');
  const [city, setCity] = useState('');
  const [organization, setOrganization] = useState('');
  const [validDays, setValidDays] = useState('');

  // Let's Encrypt fields
  const [leMethodId, setLeMethodId] = useState('netzint');
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [email, setEmail] = useState('');
  const [acmeDnsRegistration, setAcmeDnsRegistration] = useState<AcmeDnsRegistration | null>(null);

  const leMethod = LE_METHODS.find((m) => m.id === leMethodId) ?? LE_METHODS[0];

  // Let's-Encrypt-Staging-Test
  const [testStatus, setTestStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle');
  const [testLog, setTestLog] = useState<string[]>([]);
  const testCleanupRef = useRef<(() => void) | null>(null);

  useEffect(
    () => () => {
      if (testCleanupRef.current) testCleanupRef.current();
    },
    [],
  );

  const resetTest = useCallback(() => {
    if (testCleanupRef.current) testCleanupRef.current();
    testCleanupRef.current = null;
    setTestStatus('idle');
    setTestLog([]);
  }, []);

  // Upload fields
  const [certFile, setCertFile] = useState<File | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);

  const resetStatus = useCallback(() => {
    setStatus('idle');
    setErrorMessage('');
    setAcmeDnsRegistration(null);
    setCertificateConfigured(false);
  }, [setCertificateConfigured]);

  const handleCertTypeChange = useCallback(
    (type: CertType) => {
      setCertType(type);
      resetStatus();
    },
    [resetStatus],
  );

  const isSsValid =
    countryCode.trim() !== '' &&
    state.trim() !== '' &&
    city.trim() !== '' &&
    organization.trim() !== '' &&
    validDays.trim() !== '' &&
    Number(validDays) > 0;

  const credentialsValid = (leMethod.fields ?? []).every(
    (f) => f.optional || (credentials[f.env] ?? '').trim() !== '',
  );
  const isLeValid = email.trim() !== '' && credentialsValid;

  const isUploadValid = certFile !== null && keyFile !== null;

  const handleGenerateSs = useCallback(async () => {
    setStatus('loading');
    const result = await createSsCertificate({
      countrycode: countryCode,
      state,
      city,
      organization,
      valid_days: Number(validDays),
    });
    if (result.status) {
      setStatus('success');
      setCertificateConfigured(true);
    } else {
      setStatus('error');
      setErrorMessage(result.message);
    }
  }, [countryCode, state, city, organization, validDays, setCertificateConfigured]);

  const handleCreateLe = useCallback(async () => {
    setStatus('loading');
    setAcmeDnsRegistration(null);
    const result = await createLeCertificate({
      email,
      challenge: leMethod.kind === 'http' ? 'http' : 'dns',
      dns_provider: leMethod.id,
      credentials: leMethod.kind === 'dns' ? credentials : {},
    });
    if (result.status) {
      setStatus('success');
      setCertificateConfigured(true);
      const reg = result.registration as unknown;
      if (reg) {
        setAcmeDnsRegistration(reg as AcmeDnsRegistration);
      }
    } else {
      setStatus('error');
      setErrorMessage(result.message);
    }
  }, [email, leMethod, credentials, setCertificateConfigured]);

  const handleTestLe = useCallback(async () => {
    if (testCleanupRef.current) testCleanupRef.current();
    setTestStatus('running');
    setTestLog([]);
    const cleanup = await testLeCertificate(
      {
        email,
        challenge: leMethod.kind === 'http' ? 'http' : 'dns',
        dns_provider: leMethod.id,
        credentials: leMethod.kind === 'dns' ? credentials : {},
        domain: edulutionExternalDomain,
      },
      (line) => setTestLog((l) => [...l, line]),
      () => setTestStatus('success'),
      (error) => {
        setTestLog((l) => [...l, `[FEHLER] ${error}`]);
        setTestStatus('error');
      },
    );
    testCleanupRef.current = cleanup;
  }, [email, leMethod, credentials, edulutionExternalDomain]);

  const handleUpload = useCallback(async () => {
    if (!certFile || !keyFile) return;
    setStatus('loading');
    const result = await uploadCertificate(certFile, keyFile);
    if (result.status) {
      setStatus('success');
      setCertificateConfigured(true);
    } else {
      setStatus('error');
      setErrorMessage(result.message);
    }
  }, [certFile, keyFile, setCertificateConfigured]);

  const getStatusIcon = () => {
    if (status === 'loading') {
      return (
        <FontAwesomeIcon
          icon={faSpinner}
          spin
          className="text-gray-500"
        />
      );
    }
    if (status === 'success') {
      return (
        <FontAwesomeIcon
          icon={faCircleCheck}
          className="text-green-500"
        />
      );
    }
    if (status === 'error') {
      return (
        <FontAwesomeIcon
          icon={faCircleXmark}
          className="text-red-500"
          title={errorMessage}
        />
      );
    }
    return null;
  };

  const statusIcon = getStatusIcon();

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg bg-green-50 p-3 text-sm text-green-800">{t('certificateForm.noProxyInfo')}</div>

      {/* Self-Signed */}
      <label
        htmlFor="cert_type_self_signed"
        className="flex cursor-pointer items-center gap-2 text-sm font-bold text-gray-800"
      >
        <input
          id="cert_type_self_signed"
          type="radio"
          name="certificate_type"
          checked={certType === 'self-signed'}
          onChange={() => handleCertTypeChange('self-signed')}
          className="accent-primary"
        />
        {t('certificateForm.selfSigned')}
      </label>
      {certType === 'self-signed' && (
        <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
            <span className="text-sm text-gray-600">{t('common.domain')}</span>
            <Input
              variant="login"
              value={edulutionExternalDomain}
              readOnly
            />
            <span className="text-sm text-gray-600">{t('certificateForm.countryCode')}</span>
            <Input
              variant="login"
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
              className={countryCode.trim() ? 'valid-input' : ''}
            />
            <span className="text-sm text-gray-600">{t('common.state')}</span>
            <Input
              variant="login"
              value={state}
              onChange={(e) => setState(e.target.value)}
              className={state.trim() ? 'valid-input' : ''}
            />
            <span className="text-sm text-gray-600">{t('certificateForm.city')}</span>
            <Input
              variant="login"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className={city.trim() ? 'valid-input' : ''}
            />
            <span className="text-sm text-gray-600">{t('certificateForm.organization')}</span>
            <Input
              variant="login"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              className={organization.trim() ? 'valid-input' : ''}
            />
            <span className="text-sm text-gray-600">{t('certificateForm.validDays')}</span>
            <Input
              variant="login"
              type="number"
              value={validDays}
              onChange={(e) => setValidDays(e.target.value)}
              className={validDays.trim() && Number(validDays) > 0 ? 'valid-input' : ''}
            />
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="btn-security"
              size="md"
              className="text-white"
              onClick={() => {
                void handleGenerateSs();
              }}
              disabled={!isSsValid || status === 'loading'}
            >
              {t('certificateForm.generateCertificate')}
            </Button>
            {statusIcon}
          </div>
        </div>
      )}

      {/* Let's Encrypt */}
      <label
        htmlFor="cert_type_letsencrypt"
        className="flex cursor-pointer items-center gap-2 text-sm font-bold text-gray-800"
      >
        <input
          id="cert_type_letsencrypt"
          type="radio"
          name="certificate_type"
          checked={certType === 'letsencrypt'}
          onChange={() => handleCertTypeChange('letsencrypt')}
          className="accent-primary"
        />
        {t('certificateForm.letsEncrypt')}
      </label>
      {certType === 'letsencrypt' && (
        <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
            <span className="text-sm text-gray-600">{t('certificateForm.dnsProvider')}</span>
            <select
              value={leMethodId}
              onChange={(e) => {
                setLeMethodId(e.target.value);
                setCredentials({});
                resetStatus();
                resetTest();
              }}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800"
            >
              {LE_METHODS.map((m) => (
                <option
                  key={m.id}
                  value={m.id}
                >
                  {m.label}
                </option>
              ))}
            </select>
            <span className="text-sm text-gray-600">{t('common.domain')}</span>
            <Input
              variant="login"
              value={edulutionExternalDomain}
              readOnly
            />
            <span className="text-sm text-gray-600">{t('certificateForm.email')}</span>
            <Input
              variant="login"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={email.trim() ? 'valid-input' : ''}
            />
            {(leMethod.fields ?? []).map((f) => (
              <Fragment key={f.env}>
                <span className="text-sm text-gray-600">{f.label}</span>
                <Input
                  variant="login"
                  type={f.secret ? 'password' : 'text'}
                  value={credentials[f.env] ?? ''}
                  onChange={(e) => setCredentials((c) => ({ ...c, [f.env]: e.target.value }))}
                  className={f.optional || (credentials[f.env] ?? '').trim() ? 'valid-input' : ''}
                />
              </Fragment>
            ))}
          </div>

          {leMethod.kind === 'http' && (
            <p className="text-xs text-gray-500">{t('certificateForm.leHttpHint')}</p>
          )}
          {leMethod.kind === 'dns' && (
            <p className="text-xs text-gray-500">{t('certificateForm.leDnsCredentialsHint')}</p>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="btn-security"
              size="md"
              className="text-white"
              onClick={() => {
                void handleCreateLe();
              }}
              disabled={!isLeValid || status === 'loading'}
            >
              {t('certificateForm.createCertificate')}
            </Button>
            <Button
              variant="btn-outline"
              size="md"
              onClick={() => {
                void handleTestLe();
              }}
              disabled={
                !isLeValid ||
                testStatus === 'running' ||
                (leMethod.kind === 'acme-dns' && !acmeDnsRegistration)
              }
            >
              {testStatus === 'running' ? t('certificateForm.leTestRunning') : t('certificateForm.leTest')}
            </Button>
            {statusIcon}
          </div>

          {leMethod.kind === 'acme-dns' && !acmeDnsRegistration && (
            <p className="text-xs text-gray-500">{t('certificateForm.leTestNetzintHint')}</p>
          )}

          {testLog.length > 0 && (
            <div className="max-h-48 overflow-y-auto rounded-lg bg-gray-900 p-3 font-mono text-xs text-green-400">
              {testLog.map((line, i) => (
                <div
                  key={i}
                  className={line.includes('[FEHLER]') ? 'text-red-400' : ''}
                >
                  {line}
                </div>
              ))}
              {testStatus === 'running' && <div className="animate-pulse text-gray-500">_</div>}
            </div>
          )}
          {testStatus === 'success' && (
            <div className="rounded-lg bg-green-50 p-3 text-sm text-green-800">
              {t('certificateForm.leTestSuccess')}
            </div>
          )}

          {acmeDnsRegistration && (
            <div className="flex flex-col gap-2 rounded-lg border border-blue-200 bg-blue-50 p-4">
              <p className="text-sm font-bold text-blue-800">{t('certificateForm.acmeSuccess')}</p>
              <p className="text-sm text-blue-800">{t('certificateForm.acmeCnameInstruction')}</p>
              <div className="rounded bg-white p-3 font-mono text-xs text-gray-800">
                <span className="font-bold">_acme-challenge.{edulutionExternalDomain}</span> &rarr;{' '}
                <span className="font-bold">{acmeDnsRegistration.fulldomain}</span>
              </div>
              <p className="mt-2 text-sm font-bold text-blue-800">{t('certificateForm.registrationData')}</p>
              <div className="overflow-x-auto rounded bg-white p-3 font-mono text-xs text-gray-800">
                <table className="w-full">
                  <tbody>
                    <tr>
                      <td className="pr-3 font-bold">{t('certificateForm.username')}</td>
                      <td className="select-all">{acmeDnsRegistration.username}</td>
                    </tr>
                    <tr>
                      <td className="pr-3 font-bold">{t('common.password')}</td>
                      <td className="select-all">{acmeDnsRegistration.password}</td>
                    </tr>
                    <tr>
                      <td className="pr-3 font-bold">{t('certificateForm.fulldomain')}</td>
                      <td className="select-all">{acmeDnsRegistration.fulldomain}</td>
                    </tr>
                    <tr>
                      <td className="pr-3 font-bold">{t('certificateForm.subdomain')}</td>
                      <td className="select-all">{acmeDnsRegistration.subdomain}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="mt-1 text-xs text-blue-600">{t('certificateForm.acmeTraefikNote')}</p>
            </div>
          )}
        </div>
      )}

      {/* Upload */}
      <label
        htmlFor="cert_type_upload"
        className="flex cursor-pointer items-center gap-2 text-sm font-bold text-gray-800"
      >
        <input
          id="cert_type_upload"
          type="radio"
          name="certificate_type"
          checked={certType === 'upload'}
          onChange={() => handleCertTypeChange('upload')}
          className="accent-primary"
        />
        {t('certificateForm.uploadCertificate')}
      </label>
      {certType === 'upload' && (
        <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
            <span className="text-sm text-gray-600">{t('certificateForm.certFile')}</span>
            <input
              type="file"
              accept=".crt,.pem,.cer,.cert"
              onChange={(e) => setCertFile(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800"
            />
            <span className="text-sm text-gray-600">{t('certificateForm.certKey')}</span>
            <input
              type="file"
              accept=".key,.pem"
              onChange={(e) => setKeyFile(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800"
            />
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="btn-security"
              className="text-white"
              size="md"
              onClick={() => {
                void handleUpload();
              }}
              disabled={!isUploadValid || status === 'loading'}
            >
              {t('certificateForm.uploadFiles')}
            </Button>
            {statusIcon}
          </div>
        </div>
      )}
    </div>
  );
};

export default CertificateForm;
