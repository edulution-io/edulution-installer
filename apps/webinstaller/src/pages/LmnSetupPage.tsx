import { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@edulution-io/ui-kit';
import { Input } from '@shared-ui';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner, faCircleCheck, faCircleXmark } from '@fortawesome/free-solid-svg-icons';
import useInstallerStore from '../store/useInstallerStore';
import { bootstrapLmnServer, checkLmnRequirements } from '../api/installerApi';
import type { RequirementsResponse } from '../api/installerApi';
import StatusCard from '../components/StatusCard';

const LmnSetupPage = () => {
  const navigate = useNavigate();
  const store = useInstallerStore();

  const [host, setHost] = useState(store.lmnSshHost);
  const [port, setPort] = useState(store.lmnSshPort);
  const [user, setUser] = useState(store.lmnSshUser);
  const [password, setPassword] = useState(store.lmnSshPassword);

  const [requirements, setRequirements] = useState<RequirementsResponse | null>(null);
  const [checkingRequirements, setCheckingRequirements] = useState(false);

  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [store.lmnOutputLog]);

  const isValidSsh = host.trim() !== '' && port > 0 && port <= 65535 && user.trim() !== '' && password.trim() !== '';

  const handleBootstrap = useCallback(async () => {
    if (!isValidSsh) return;

    store.setLmnSsh({ host, port, user, password });
    store.setLmnBootstrapStatus('running');
    store.clearLmnOutput();

    await bootstrapLmnServer(
      { host, port, user, password },
      (line) => store.appendLmnOutput(line),
      () => store.setLmnBootstrapStatus('completed'),
      (error) => {
        store.appendLmnOutput(`[ERROR] ${error}`);
        store.setLmnBootstrapStatus('failed');
      },
    );
  }, [isValidSsh, host, port, user, password, store]);

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
      <h3 className="text-lg font-bold text-gray-800">Linuxmuster-Server einrichten</h3>

      <div>
        <label
          htmlFor="ssh_host"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          SSH Host:
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
            SSH Port:
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
            SSH Benutzer:
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
          SSH Passwort:
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
              Bootstrap wird ausgefuehrt...
            </>
          )}
          {!bootstrapRunning && bootstrapFailed && 'Bootstrap erneut starten'}
          {!bootstrapRunning && !bootstrapFailed && 'Bootstrap starten'}
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
          Bootstrap erfolgreich abgeschlossen
        </div>
      )}

      {bootstrapFailed && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800">
          <FontAwesomeIcon
            icon={faCircleXmark}
            className="text-red-500"
          />
          Bootstrap fehlgeschlagen
        </div>
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
              Requirements werden geprueft...
            </>
          ) : (
            'Requirements pruefen'
          )}
        </Button>
      )}

      {requirements && (
        <div className="flex flex-col gap-2">
          <h4 className="text-sm font-bold text-gray-800">System-Anforderungen</h4>
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
          onClick={() => navigate('/lmn-install')}
        >
          Installation starten
        </Button>
      )}

      {requirements && !store.lmnRequirementsPassed && (
        <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-800">
          Nicht alle Anforderungen erfuellt. Bitte behebe die Probleme und pruefe erneut.
        </div>
      )}

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate('/token')}
        disabled={bootstrapRunning}
      >
        Zurück
      </Button>
    </div>
  );
};

export default LmnSetupPage;
