import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faServer } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@edulution-io/ui-kit';
import { Card, CardContent } from '@shared-ui';
import type { DeploymentTarget } from '@shared-types';
import useInstallerStore from '../store/useInstallerStore';
import { checkToken } from '../api/installerApi';

type Step = 'adType' | 'tokenEntry';

const TokenPage = () => {
  const navigate = useNavigate();
  const store = useInstallerStore();

  const [step, setStep] = useState<Step>('adType');
  const [adType, setAdType] = useState<'existing' | 'new' | ''>(store.adType ?? '');
  const [target, setTarget] = useState<DeploymentTarget>(store.deploymentTarget ?? 'linuxmuster');

  const [token, setToken] = useState('');
  const [tokenValid, setTokenValid] = useState(false);
  const [checking, setChecking] = useState(false);

  const handleTokenChange = useCallback(async (value: string) => {
    setToken(value);
    if (!value.trim()) {
      setTokenValid(false);
      return;
    }
    setChecking(true);
    const result = await checkToken(value);
    setTokenValid(result === true);
    setChecking(false);
  }, []);

  const handleSubmitToken = useCallback(() => {
    if (!adType) return;
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
  }, [adType, target, token, store, navigate]);

  const handleManualEntry = useCallback(() => {
    if (!adType) return;
    store.setAdType(adType);
    store.setDeploymentTarget(target);
    store.setTokenData({ lmnExternalDomain: '', lmnBinduserDn: '', lmnBinduserPw: '' });
    void navigate('/configure');
  }, [adType, target, store, navigate]);

  const handleNewAd = useCallback(() => {
    store.setAdType('new');
    store.setDeploymentTarget('linuxmuster');
    void navigate('/lmn-setup');
  }, [store, navigate]);

  const handleNext = useCallback(() => {
    if (!adType) return;
    console.info('Selected AD Type:', adType);
    if (adType === 'new') {
      console.info('Selected Deployment Target:', target);
      handleNewAd();
    } else if (target === 'linuxmuster') {
      console.info('Selected Deployment Target:', target);
      setStep('tokenEntry');
    } else {
      console.info('Selected Deployment Target:', 'manual');
      handleManualEntry();
    }
  }, [adType, target, handleNewAd, handleManualEntry]);

  // Step 1: AD type + deployment target
  if (step === 'adType') {
    return (
      <div className="flex flex-col gap-4">
        <div>
          <label
            htmlFor="adType"
            className="mb-1 block text-sm font-bold text-gray-800"
          >
            Verzeichnisdienst anbinden
          </label>
          <select
            id="adType"
            value={adType}
            onChange={(e) => setAdType(e.target.value as typeof adType)}
            className="w-full cursor-pointer rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm"
          >
            <option
              value=""
              disabled
            >
              Bitte wählen…
            </option>
            <option value="existing">Bestehenden Verzeichnisdienst anbinden</option>
            <option value="new">linuxmuster.net aufsetzen</option>
          </select>
        </div>

        {adType === 'existing' && (
          <div>
            <span className="mb-2 block text-sm font-bold text-gray-800">
              Welcher Verzeichnisdienst wird verwendet?
            </span>
            <div className="grid grid-cols-2 gap-3">
              <Card
                variant={target === 'linuxmuster' ? 'gridSelected' : 'text'}
                className="cursor-pointer"
                onClick={() => setTarget('linuxmuster')}
              >
                <CardContent className="flex flex-col items-center justify-center gap-2 p-4">
                  <img
                    src="/img/edu_Linuxmuster.svg"
                    alt="linuxmuster.net Logo"
                    className="h-12 w-12 dark:invert-0"
                    style={{ filter: 'brightness(0)' }}
                  />
                  <span className="text-sm font-medium">linuxmuster.net</span>
                </CardContent>
              </Card>
              <Card
                variant={target === 'generic' ? 'gridSelected' : 'text'}
                className="cursor-pointer"
                onClick={() => setTarget('generic')}
              >
                <CardContent className="flex flex-col items-center justify-center gap-2 p-4">
                  <div className="flex h-12 w-12 items-center justify-center">
                    <FontAwesomeIcon
                      icon={faServer}
                      className="text-3xl"
                    />
                  </div>
                  <span className="text-sm font-medium">Generisch</span>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {target === 'linuxmuster' ? (
          <p className="mt-2 text-sm text-gray-600">
            Hier kann im nächsten Schritt entweder ein edulution Setup-Token eingegeben oder die Konfiguration manuell
            durchgeführt werden.
          </p>
        ) : (
          <p className="mt-2 text-sm text-gray-600">
            Hier kann ein Verzeichnisdienst mit Active Directory angebunden werden.
          </p>
        )}

        <Button
          variant="btn-security"
          size="lg"
          className="mt-2 w-full justify-center text-white"
          onClick={handleNext}
          disabled={!adType}
        >
          Weiter
        </Button>

        <Button
          variant="btn-outline"
          size="lg"
          className="w-full justify-center"
          onClick={() => navigate('/organization')}
        >
          Zurück
        </Button>
      </div>
    );
  }

  // Step 2: Token entry (only for existing AD + linuxmuster.net)
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
          onChange={(e) => {
            void handleTokenChange(e.target.value);
          }}
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
        onClick={() => setStep('adType')}
      >
        Zurück
      </Button>
    </div>
  );
};

export default TokenPage;
