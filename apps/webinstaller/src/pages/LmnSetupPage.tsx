import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@edulution-io/ui-kit';
import { Input } from '@shared-ui';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner, faCircleCheck, faCircleXmark, faCircleInfo } from '@fortawesome/free-solid-svg-icons';
import useInstallerStore from '../store/useInstallerStore';
import { bootstrapLmnServer, checkLmnRequirements, checkLmnConnection } from '../api/installerApi';
import type { RequirementsResponse } from '../api/installerApi';
import StatusCard from '../components/StatusCard';

const LmnSetupPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const store = useInstallerStore();

  const [host, setHost] = useState(store.lmnSshHost);
  const [port, setPort] = useState(store.lmnSshPort);
  const [user, setUser] = useState(store.lmnSshUser);
  const [password, setPassword] = useState(store.lmnSshPassword);

  const [requirements, setRequirements] = useState<RequirementsResponse | null>(null);
  const [checkingRequirements, setCheckingRequirements] = useState(false);
  const [checkingConnection, setCheckingConnection] = useState(false);

  const logRef = useRef<HTMLDivElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [store.lmnOutputLog]);

  useEffect(() => () => {
    if (cleanupRef.current) cleanupRef.current();
  }, []);

  const isValidSsh = host.trim() !== '' && port > 0 && port <= 65535 && user.trim() !== '' && password.trim() !== '';

  const handleBootstrap = useCallback(async () => {
    if (!isValidSsh) return;

    store.setLmnSsh({ host, port, user, password });
    store.setLmnBootstrapStatus('running');
    store.clearLmnOutput();

    const cleanup = await bootstrapLmnServer(
      { host, port, user, password },
      (line) => store.appendLmnOutput(line),
      () => store.setLmnBootstrapStatus('completed'),
      (error) => {
        store.appendLmnOutput(`[ERROR] ${error}`);
        store.setLmnBootstrapStatus('failed');
      },
    );
    cleanupRef.current = cleanup;
  }, [isValidSsh, host, port, user, password, store]);

  const handleCheckConnection = useCallback(async () => {
    if (!host.trim()) return;
    setCheckingConnection(true);
    try {
      const result = await checkLmnConnection(host);
      if (result.status) {
        store.setLmnSsh({ host, port, user, password });
        store.setLmnBootstrapStatus('completed');
        store.appendLmnOutput(t('lmnSetup.connectionRestored'));
      } else {
        store.appendLmnOutput(`[ERROR] ${result.message}`);
      }
    } catch {
      store.appendLmnOutput(`[ERROR] ${t('lmnSetup.connectionCheckFailed')}`);
    }
    setCheckingConnection(false);
  }, [host, port, user, password, store, t]);

  const handleCheckRequirements = useCallback(async () => {
    setCheckingRequirements(true);
    try {
      const result = await checkLmnRequirements('linuxmuster.yml');
      setRequirements(result);
      store.setLmnRequirementsPassed(result.all_passed);
    } catch {
      store.setLmnRequirementsPassed(false);
    }
    setCheckingRequirements(false);
  }, [store]);

  const bootstrapRunning = store.lmnBootstrapStatus === 'running';
  const bootstrapDone = store.lmnBootstrapStatus === 'completed';
  const bootstrapFailed = store.lmnBootstrapStatus === 'failed';

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-bold text-gray-800">{t('lmnSetup.title')}</h3>

      <div className="flex gap-3 rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
        <FontAwesomeIcon
          icon={faCircleInfo}
          className="mt-0.5 shrink-0 text-blue-500"
        />
        <div>
          <p className="font-bold">{t('lmnSetup.requirementsTitle')}</p>
          <ul className="mt-1 list-inside list-disc space-y-0.5">
            <li>{t('lmnSetup.reqOs')}</li>
            <li>{t('lmnSetup.reqRam')}</li>
            <li>{t('lmnSetup.reqDisks')}</li>
          </ul>
        </div>
      </div>

      <div>
        <label
          htmlFor="ssh_host"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          {t('lmnSetup.sshHost')}
        </label>
        <Input
          id="ssh_host"
          variant="login"
          value={host}
          onChange={(e) => setHost(e.target.value)}
          className={host.trim() ? 'valid-input' : ''}
          disabled={bootstrapRunning}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label
            htmlFor="ssh_port"
            className="mb-1 block text-sm font-bold text-gray-800"
          >
            {t('lmnSetup.sshPort')}
          </label>
          <Input
            id="ssh_port"
            variant="login"
            type="number"
            min={1}
            max={65535}
            value={port}
            onChange={(e) => setPort(Number(e.target.value))}
            disabled={bootstrapRunning}
          />
        </div>

        <div>
          <label
            htmlFor="ssh_user"
            className="mb-1 block text-sm font-bold text-gray-800"
          >
            {t('lmnSetup.sshUser')}
          </label>
          <Input
            id="ssh_user"
            variant="login"
            value={user}
            onChange={(e) => setUser(e.target.value)}
            disabled={bootstrapRunning}
          />
        </div>
      </div>

      <div>
        <label
          htmlFor="ssh_password"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          {t('lmnSetup.sshPassword')}
        </label>
        <Input
          id="ssh_password"
          variant="login"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className={password.trim() ? 'valid-input' : ''}
          disabled={bootstrapRunning}
        />
      </div>

      {!bootstrapDone && (
        <Button
          variant="btn-security"
          size="lg"
          className="mt-2 w-full justify-center text-white"
          onClick={() => {
            void handleBootstrap();
          }}
          disabled={!isValidSsh || bootstrapRunning}
        >
          {bootstrapRunning && (
            <>
              <FontAwesomeIcon
                icon={faSpinner}
                spin
                className="mr-2"
              />
              {t('lmnSetup.bootstrapRunning')}
            </>
          )}
          {!bootstrapRunning && bootstrapFailed && t('lmnSetup.bootstrapRetry')}
          {!bootstrapRunning && !bootstrapFailed && t('lmnSetup.bootstrapStart')}
        </Button>
      )}

      {store.lmnOutputLog.length > 0 && (
        <div
          ref={logRef}
          className="max-h-48 overflow-y-auto rounded-lg bg-gray-900 p-3 font-mono text-xs text-green-400"
        >
          {store.lmnOutputLog.map((line) => (
            <div
              key={line.id}
              className={line.text.includes('[ERROR]') ? 'text-red-400' : ''}
            >
              {line.text}
            </div>
          ))}
        </div>
      )}

      {bootstrapDone && (
        <div className="flex items-center gap-2 rounded-lg bg-green-50 p-3 text-sm text-green-800">
          <FontAwesomeIcon
            icon={faCircleCheck}
            className="text-green-500"
          />
          {t('lmnSetup.bootstrapSuccess')}
        </div>
      )}

      {bootstrapFailed && (
        <>
          <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800">
            <FontAwesomeIcon
              icon={faCircleXmark}
              className="text-red-500"
            />
            {t('lmnSetup.bootstrapFailed')}
          </div>
          <Button
            variant="btn-outline"
            size="lg"
            className="w-full justify-center"
            onClick={() => {
              void handleCheckConnection();
            }}
            disabled={!host.trim() || checkingConnection}
          >
            {checkingConnection ? (
              <>
                <FontAwesomeIcon
                  icon={faSpinner}
                  spin
                  className="mr-2"
                />
                {t('lmnSetup.checkingConnection')}
              </>
            ) : (
              t('lmnSetup.checkConnection')
            )}
          </Button>
        </>
      )}

      {bootstrapDone && !requirements && (
        <Button
          variant="btn-security"
          size="lg"
          className="w-full justify-center text-white"
          onClick={() => {
            void handleCheckRequirements();
          }}
          disabled={checkingRequirements}
        >
          {checkingRequirements ? (
            <>
              <FontAwesomeIcon
                icon={faSpinner}
                spin
                className="mr-2"
              />
              {t('lmnSetup.checkingRequirements')}
            </>
          ) : (
            t('lmnSetup.checkRequirements')
          )}
        </Button>
      )}

      {requirements && (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-bold text-gray-800">{t('lmnSetup.systemRequirements')}</h4>
          {requirements.checks.map((check) => (
            <StatusCard
              key={check.name}
              label={check.message}
              status={{ status: check.status === 'passed', message: check.message }}
              loading={false}
              onRetry={() => {
                void handleCheckRequirements();
              }}
            />
          ))}
        </div>
      )}

      {requirements && store.lmnRequirementsPassed && (
        <Button
          variant="btn-security"
          size="lg"
          className="mt-2 w-full justify-center text-white"
          onClick={() => navigate('/lmn-config')}
        >
          {t('common.startInstallation')}
        </Button>
      )}

      {requirements && !store.lmnRequirementsPassed && (
        <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-800">
          {t('lmnSetup.requirementsNotMet')}
        </div>
      )}

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate('/token')}
        disabled={bootstrapRunning}
      >
        {t('common.back')}
      </Button>
    </div>
  );
};

export default LmnSetupPage;
