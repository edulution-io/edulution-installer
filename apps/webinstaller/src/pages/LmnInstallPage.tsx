import { useEffect, useRef, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@edulution-io/ui-kit';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner, faCircleCheck, faCircleXmark } from '@fortawesome/free-solid-svg-icons';
import useInstallerStore from '../store/useInstallerStore';
import { startLmnPlaybook, createLmnWebSocket } from '../api/installerApi';

const LmnInstallPage = () => {
  const navigate = useNavigate();
  const store = useInstallerStore();
  const logRef = useRef<HTMLDivElement>(null);
  const [started, setStarted] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [store.lmnOutputLog]);

  const startInstallation = useCallback(async () => {
    if (started) return;
    setStarted(true);
    store.clearLmnOutput();
    store.setLmnPlaybookStatus('running');

    // Connect WebSocket first
    const ws = createLmnWebSocket();
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as { type: string; data: string };
        if (msg.type === 'stdout' || msg.type === 'stderr') {
          store.appendLmnOutput(msg.data);
        } else if (msg.type === 'status') {
          if (msg.data === 'successful' || msg.data === 'completed') {
            store.setLmnPlaybookStatus('completed');
          } else if (msg.data === 'failed') {
            store.setLmnPlaybookStatus('failed');
          }
        } else if (msg.type === 'event') {
          store.appendLmnOutput(msg.data);
        }
      } catch {
        store.appendLmnOutput(event.data as string);
      }
    };

    ws.onclose = () => {
      const currentStatus = useInstallerStore.getState().lmnPlaybookStatus;
      if (currentStatus === 'running') {
        // WS closed while still running - the LMN API shuts itself down after completion
        useInstallerStore.getState().setLmnPlaybookStatus('completed');
      }
    };

    ws.onerror = () => {
      // WebSocket error - might happen if LMN API shuts down after completion
    };

    // Start the playbook
    try {
      const currentStore = useInstallerStore.getState();
      await startLmnPlaybook('linuxmuster.yml', {
        lmn_server_ip: currentStore.lmnServerIp,
        lmn_netmask: currentStore.lmnNetmask,
        lmn_gateway: currentStore.lmnGateway,
        lmn_servername: currentStore.lmnServername,
        lmn_domainname: currentStore.lmnDomainname,
        lmn_schoolname: currentStore.lmnSchoolname,
        lmn_location: currentStore.lmnLocation,
        lmn_country: currentStore.lmnCountry,
        lmn_state: currentStore.lmnState,
        lmn_dhcprange: currentStore.lmnDhcprange,
        lmn_adminpw: currentStore.lmnAdminpw,
        lmn_timezone: currentStore.lmnTimezone,
        lmn_locale: currentStore.lmnLocale,
      });
    } catch {
      store.appendLmnOutput('[ERROR] Playbook konnte nicht gestartet werden');
      store.setLmnPlaybookStatus('failed');
    }
  }, [started, store]);

  useEffect(() => {
    void startInstallation();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const isRunning = store.lmnPlaybookStatus === 'running';
  const isCompleted = store.lmnPlaybookStatus === 'completed';
  const isFailed = store.lmnPlaybookStatus === 'failed';

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-bold text-gray-800">Linuxmuster Installation</h3>

      <div className="flex items-center gap-2 text-sm text-gray-600">
        {isRunning && (
          <>
            <FontAwesomeIcon
              icon={faSpinner}
              spin
              className="text-gray-500"
            />
            Installation laeuft...
          </>
        )}
        {isCompleted && (
          <>
            <FontAwesomeIcon
              icon={faCircleCheck}
              className="text-green-500"
            />
            <span className="text-green-700">Installation erfolgreich abgeschlossen</span>
          </>
        )}
        {isFailed && (
          <>
            <FontAwesomeIcon
              icon={faCircleXmark}
              className="text-red-500"
            />
            <span className="text-red-700">Installation fehlgeschlagen</span>
          </>
        )}
      </div>

      <div
        ref={logRef}
        className="h-72 overflow-y-auto rounded-lg bg-gray-900 p-3 font-mono text-xs text-green-400"
      >
        {store.lmnOutputLog.map((line) => (
          <div
            key={line.id}
            className={line.text.includes('[ERROR]') || line.text.includes('FAILED') ? 'text-red-400' : ''}
          >
            {line.text}
          </div>
        ))}
        {isRunning && <div className="animate-pulse text-gray-500">_</div>}
      </div>

      {isCompleted && (
        <Button
          variant="btn-security"
          size="lg"
          className="w-full justify-center text-white"
          onClick={() => navigate('/certificate')}
        >
          Weiter
        </Button>
      )}

      {isFailed && (
        <Button
          variant="btn-outline"
          size="lg"
          className="w-full justify-center"
          onClick={() => navigate('/lmn-setup')}
        >
          Zurück zur Einrichtung
        </Button>
      )}
    </div>
  );
};

export default LmnInstallPage;
