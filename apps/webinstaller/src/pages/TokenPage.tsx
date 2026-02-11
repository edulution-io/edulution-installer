import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@edulution-io/ui-kit';
import useInstallerStore from '../store/useInstallerStore';
import { checkToken } from '../api/installerApi';

type Step = 'organization' | 'adType' | 'deploymentTarget' | 'tokenEntry';

const TokenPage = () => {
  const navigate = useNavigate();
  const store = useInstallerStore();

  const [step, setStep] = useState<Step>('organization');
  const [orgType, setOrgType] = useState<'schule' | 'unternehmen' | 'verwaltung'>(store.organizationType ?? 'schule');
  const [adType, setAdType] = useState<'existing' | 'new'>(store.adType ?? 'existing');
  const [target, setTarget] = useState<'linuxmuster' | 'generic'>(store.deploymentTarget ?? 'linuxmuster');

  const [token, setToken] = useState('');
  const [tokenValid, setTokenValid] = useState(false);
  const [checking, setChecking] = useState(false);

  const handleTokenChange = useCallback(
    async (value: string) => {
      setToken(value);
      if (!value.trim()) {
        setTokenValid(false);
        return;
      }
      setChecking(true);
      const result = await checkToken(value);
      setTokenValid(result === true);
      setChecking(false);
    },
    [],
  );

  const handleSubmitToken = useCallback(() => {
    store.setOrganizationType(orgType);
    store.setAdType(adType);
    store.setDeploymentTarget(target);
    if (token) {
      try {
        const decoded = JSON.parse(atob(token)) as {
          external_domain?: string;
          binduser_dn?: string;
          binduser_password?: string;
        };
        store.setTokenData({
          lmnExternalDomain: decoded.external_domain ?? '',
          lmnBinduserDn: decoded.binduser_dn ?? '',
          lmnBinduserPw: decoded.binduser_password ?? '',
        });
      } catch {
        store.setTokenData({ lmnExternalDomain: '', lmnBinduserDn: '', lmnBinduserPw: '' });
      }
    }
    void navigate('/configure');
  }, [orgType, adType, target, token, store, navigate]);

  const handleManualEntry = useCallback(() => {
    store.setOrganizationType(orgType);
    store.setAdType(adType);
    store.setDeploymentTarget(target);
    store.setTokenData({ lmnExternalDomain: '', lmnBinduserDn: '', lmnBinduserPw: '' });
    void navigate('/configure');
  }, [orgType, adType, target, store, navigate]);

  const handleNewAd = useCallback(() => {
    store.setOrganizationType(orgType);
    store.setAdType('new');
    store.setDeploymentTarget('linuxmuster');
    void navigate('/lmn-setup');
  }, [orgType, store, navigate]);

  // Step 1: Organization type
  if (step === 'organization') {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <label
            htmlFor="orgType"
            className="mb-1 block text-sm font-bold text-gray-800"
          >
            Für wen ist die Installation?
          </label>
          <select
            id="orgType"
            value={orgType}
            onChange={(e) => setOrgType(e.target.value as typeof orgType)}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm"
          >
            <option value="schule">Schule</option>
            <option value="unternehmen">Unternehmen</option>
            <option value="verwaltung">Verwaltung</option>
          </select>
        </div>

        <Button
          variant="btn-security"
          size="lg"
          className="mt-2 w-full justify-center text-white"
          onClick={() => setStep('adType')}
        >
          Weiter
        </Button>

        <Button
          variant="btn-outline"
          size="lg"
          className="w-full justify-center"
          onClick={() => navigate('/')}
        >
          Zurück
        </Button>
      </div>
    );
  }

  // Step 2: AD type
  if (step === 'adType') {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <label
            htmlFor="adType"
            className="mb-1 block text-sm font-bold text-gray-800"
          >
            Active Directory Anbindung
          </label>
          <select
            id="adType"
            value={adType}
            onChange={(e) => setAdType(e.target.value as typeof adType)}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm"
          >
            <option value="existing">Bestehendes AD anbinden</option>
            <option value="new">Neues AD aufsetzen</option>
          </select>
        </div>

        <Button
          variant="btn-security"
          size="lg"
          className="mt-2 w-full justify-center text-white"
          onClick={() => {
            if (adType === 'new') {
              handleNewAd();
            } else {
              setStep('deploymentTarget');
            }
          }}
        >
          Weiter
        </Button>

        <Button
          variant="btn-outline"
          size="lg"
          className="w-full justify-center"
          onClick={() => setStep('organization')}
        >
          Zurück
        </Button>
      </div>
    );
  }

  // Step 3: Deployment target (only for existing AD)
  if (step === 'deploymentTarget') {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <label
            htmlFor="deploymentTarget"
            className="mb-1 block text-sm font-bold text-gray-800"
          >
            Welches AD wird verwendet?
          </label>
          <select
            id="deploymentTarget"
            value={target}
            onChange={(e) => setTarget(e.target.value as typeof target)}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm"
          >
            <option value="linuxmuster">Linuxmuster</option>
            <option value="generic">Generisch</option>
          </select>
        </div>

        <Button
          variant="btn-security"
          size="lg"
          className="mt-2 w-full justify-center text-white"
          onClick={() => {
            if (target === 'linuxmuster') {
              setStep('tokenEntry');
            } else {
              handleManualEntry();
            }
          }}
        >
          {target === 'linuxmuster' ? 'Weiter' : 'Manuell konfigurieren'}
        </Button>

        <Button
          variant="btn-outline"
          size="lg"
          className="w-full justify-center"
          onClick={() => setStep('adType')}
        >
          Zurück
        </Button>
      </div>
    );
  }

  // Step 4: Token entry (only for existing AD + Linuxmuster)
  return (
    <div className="flex flex-col gap-4">
      <div>
        <label
          htmlFor="edulutionsetuptoken"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          Füge hier deinen edulution Setup-Token ein:
        </label>
        <textarea
          id="edulutionsetuptoken"
          rows={5}
          value={token}
          onChange={(e) => { void handleTokenChange(e.target.value); }}
          className={`w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm ${tokenValid ? 'valid-input' : ''}`}
        />

        <Button
          variant="btn-security"
          size="lg"
          className="mt-3 w-full justify-center text-white"
          onClick={handleSubmitToken}
          disabled={!tokenValid || checking}
        >
          Überprüfen
        </Button>
      </div>

      <div className="mt-2 border-t border-gray-200 pt-4">
        <span className="mb-2 block text-sm font-bold text-gray-800">Hier gehts zur manuellen Eingabe:</span>
        <Button
          variant="btn-outline"
          size="lg"
          className="w-full justify-center"
          onClick={handleManualEntry}
        >
          Manuell eingeben
        </Button>
      </div>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => setStep('deploymentTarget')}
      >
        Zurück
      </Button>
    </div>
  );
};

export default TokenPage;
