import { useState, useCallback } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner, faCircleCheck, faCircleXmark } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@edulution-io/ui-kit';
import { Input } from '@shared-ui';
import useInstallerStore from '../store/useInstallerStore';
import { createSsCertificate, createLeCertificate, uploadCertificate } from '../api/installerApi';

type CertType = 'self-signed' | 'letsencrypt' | 'upload';
type OperationStatus = 'idle' | 'loading' | 'success' | 'error';

const CertificateForm = () => {
  const { edulutionExternalDomain, setCertificateConfigured } = useInstallerStore();

  const [certType, setCertType] = useState<CertType>('upload');
  const [status, setStatus] = useState<OperationStatus>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  // Self-signed fields
  const [countryCode, setCountryCode] = useState('');
  const [state, setState] = useState('');
  const [city, setCity] = useState('');
  const [organisation, setOrganisation] = useState('');
  const [validDays, setValidDays] = useState('');

  // Let's Encrypt fields
  const [email, setEmail] = useState('');

  // Upload fields
  const [certFile, setCertFile] = useState<File | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);

  const resetStatus = useCallback(() => {
    setStatus('idle');
    setErrorMessage('');
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
    organisation.trim() !== '' &&
    validDays.trim() !== '' &&
    Number(validDays) > 0;

  const isLeValid = email.trim() !== '';

  const isUploadValid = certFile !== null && keyFile !== null;

  const handleGenerateSs = useCallback(async () => {
    setStatus('loading');
    const result = await createSsCertificate({
      countrycode: countryCode,
      state,
      city,
      organisation,
      valid_days: Number(validDays),
    });
    if (result.status) {
      setStatus('success');
      setCertificateConfigured(true);
    } else {
      setStatus('error');
      setErrorMessage(result.message);
    }
  }, [countryCode, state, city, organisation, validDays, setCertificateConfigured]);

  const handleCreateLe = useCallback(async () => {
    setStatus('loading');
    const result = await createLeCertificate({ email });
    if (result.status) {
      setStatus('success');
      setCertificateConfigured(true);
    } else {
      setStatus('error');
      setErrorMessage(result.message);
    }
  }, [email, setCertificateConfigured]);

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
      <div className="rounded-lg bg-green-50 p-3 text-sm text-green-800">
        Du verwendest keinen Reverse-Proxy. Für edulution benötigst du ein Zertifikat, welches du hier generieren,
        erstellen oder hochladen kannst.
      </div>

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
        Selbst-Signiertes-Zertifikat generieren
      </label>
      {certType === 'self-signed' && (
        <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
            <span className="text-sm text-gray-600">Domain:</span>
            <Input
              variant="login"
              value={edulutionExternalDomain}
              readOnly
            />
            <span className="text-sm text-gray-600">Ländercode (DE):</span>
            <Input
              variant="login"
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
              className={countryCode.trim() ? 'valid-input' : ''}
            />
            <span className="text-sm text-gray-600">Bundesland:</span>
            <Input
              variant="login"
              value={state}
              onChange={(e) => setState(e.target.value)}
              className={state.trim() ? 'valid-input' : ''}
            />
            <span className="text-sm text-gray-600">Stadt:</span>
            <Input
              variant="login"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className={city.trim() ? 'valid-input' : ''}
            />
            <span className="text-sm text-gray-600">Organisation:</span>
            <Input
              variant="login"
              value={organisation}
              onChange={(e) => setOrganisation(e.target.value)}
              className={organisation.trim() ? 'valid-input' : ''}
            />
            <span className="text-sm text-gray-600">Gültigkeit (Tage):</span>
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
              className="text-white"
              onClick={() => { void handleGenerateSs(); }}
              disabled={!isSsValid || status === 'loading'}
            >
              Zertifikat generieren
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
        Zertifikat mit Let&apos;s Encrypt erstellen
      </label>
      {certType === 'letsencrypt' && (
        <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
            <span className="text-sm text-gray-600">Domain:</span>
            <Input
              variant="login"
              value={edulutionExternalDomain}
              readOnly
            />
            <span className="text-sm text-gray-600">E-Mail-Adresse:</span>
            <Input
              variant="login"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={email.trim() ? 'valid-input' : ''}
            />
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="btn-security"
              className="text-white"
              onClick={() => { void handleCreateLe(); }}
              disabled={!isLeValid || status === 'loading'}
            >
              Zertifikat erstellen
            </Button>
            {statusIcon}
          </div>
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
        Zertifikat hochladen
      </label>
      {certType === 'upload' && (
        <div className="flex flex-col gap-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
            <span className="text-sm text-gray-600">Zertifikats-Datei:</span>
            <input
              type="file"
              accept=".crt,.pem,.cer,.cert"
              onChange={(e) => setCertFile(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800"
            />
            <span className="text-sm text-gray-600">Zertifikats-Key:</span>
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
              onClick={() => { void handleUpload(); }}
              disabled={!isUploadValid || status === 'loading'}
            >
              Dateien hochladen
            </Button>
            {statusIcon}
          </div>
        </div>
      )}
    </div>
  );
};

export default CertificateForm;
