import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@edulution-io/ui-kit';
import useInstallerStore from '../store/useInstallerStore';
import { checkToken } from '../api/installerApi';

const TokenPage = () => {
  const navigate = useNavigate();
  const { deploymentTarget, setDeploymentTarget, setTokenData } = useInstallerStore();

  const [target, setTarget] = useState<'linuxmuster' | 'generic'>(deploymentTarget ?? 'linuxmuster');
  const [token, setToken] = useState('');
  const [tokenValid, setTokenValid] = useState(false);
  const [checking, setChecking] = useState(false);

  const handleTargetChange = useCallback((value: string) => {
    const t = value as 'linuxmuster' | 'generic';
    setTarget(t);
    setTokenValid(false);
  }, []);

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
    setDeploymentTarget(target);
    if (target === 'linuxmuster' && token) {
      try {
        const decoded = JSON.parse(atob(token)) as {
          external_domain?: string;
          binduser_dn?: string;
          binduser_password?: string;
        };
        setTokenData({
          lmnExternalDomain: decoded.external_domain ?? '',
          lmnBinduserDn: decoded.binduser_dn ?? '',
          lmnBinduserPw: decoded.binduser_password ?? '',
        });
      } catch {
        setTokenData({ lmnExternalDomain: '', lmnBinduserDn: '', lmnBinduserPw: '' });
      }
    }
    void navigate('/configure');
  }, [target, token, setDeploymentTarget, setTokenData, navigate]);

  const handleManualEntry = useCallback(() => {
    setDeploymentTarget(target);
    setTokenData({ lmnExternalDomain: '', lmnBinduserDn: '', lmnBinduserPw: '' });
    void navigate('/configure');
  }, [target, setDeploymentTarget, setTokenData, navigate]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <label
          htmlFor="targetType"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          Für wen ist die Installation?
        </label>
        <select
          id="targetType"
          value={target}
          onChange={(e) => handleTargetChange(e.target.value)}
          className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm"
        >
          <option value="linuxmuster">Schule</option>
          <option value="generic">Unternehmen</option>
        </select>
      </div>

      {target === 'linuxmuster' && (
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
      )}

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
    </div>
  );
};

export default TokenPage;
