import { useEffect, useRef, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@edulution-io/ui-kit';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faSpinner,
  faCircleCheck,
  faCircleXmark,
  faCircleInfo,
  faTriangleExclamation,
} from '@fortawesome/free-solid-svg-icons';
import useInstallerStore, { lmnLdapHost } from '../store/useInstallerStore';
import {
  startLmnPlaybook,
  createLmnWebSocket,
  getEdulutionConfig,
  getLmnPlaybookStatus,
  getLmnOutput,
  type LmnOutputMessage,
  checkLmnConnection,
  submitConfiguration,
  shutdownLmnInstaller,
  type ApiError,
} from '../api/installerApi';
import EdulutionDomainField from '../components/EdulutionDomainField';
import { defaultEdulutionDomain, isValidEdulutionDomain } from '../utils/edulutionDomain';

type OutputConnection = 'connected' | 'reconnecting' | 'unresponsive';

const STATUS_POLL_MS = 5000;
const STATUS_TIMEOUT_MS = 10000;
// A page of output passes the web installer's proxy as a whole, which may take a while on a slow link.
const OUTPUT_TIMEOUT_MS = 60000;
const MAX_RECONNECT_DELAY_MS = 15000;
// linuxmuster-setup rebuilds network and services on the server, which may cut the connection for a while.
const UNRESPONSIVE_AFTER_MS = 120000;
// How long a run the status reports as ended may take to replay its output up to the end.
const FINAL_REPLAY_MS = 10000;

const LmnInstallPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const store = useInstallerStore();
  const logRef = useRef<HTMLDivElement>(null);
  // The bind password is kept in memory only, so it marks a configuration fetched in this session.
  const configFetched =
    store.lmnPlaybookStatus === 'completed' && store.lmnBinduserPw !== '' && store.lmnCaCertificate !== '';
  const [configuring, setConfiguring] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [edulutionExternalDomain, setEdulutionExternalDomain] = useState(
    store.edulutionExternalDomain || defaultEdulutionDomain(),
  );
  const [connection, setConnection] = useState<OutputConnection>('connected');
  // The output comes over HTTP while the stream does not deliver.
  const [followingOverHttp, setFollowingOverHttp] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  // Counts every start and end of following a run; a response that comes back under another count is stale.
  const generationRef = useRef(0);
  const followingRef = useRef(false);
  const statusTimerRef = useRef<number | undefined>(undefined);
  const reconnectTimerRef = useRef<number | undefined>(undefined);
  const finishTimerRef = useRef<number | undefined>(undefined);
  const reconnectAttemptRef = useRef(0);
  const lastContactRef = useRef(Date.now());
  const pollInFlightRef = useRef(false);
  const connectOutputRef = useRef<() => void>(() => {});
  const pendingLinesRef = useRef<string[]>([]);
  const flushFrameRef = useRef<number | undefined>(undefined);
  const startWhenIdleRef = useRef(false);
  // Position in the run's output, the same for the stream and the HTTP fallback; the stream starts over on opening.
  const outputPositionRef = useRef(0);
  const outputJobRef = useRef<string | null>(null);
  const streamEpochRef = useRef(0);
  // Set by the stream's first message, not by opening: something on the way may open it and pass nothing.
  const streamReadyRef = useRef(false);
  const outputInFlightRef = useRef(false);
  const fetchOutputRef = useRef<() => Promise<void>>(async () => {});

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [store.lmnOutputLog]);

  // A replay brings thousands of lines at once; one store update per frame keeps the page responsive.
  const flushLines = useCallback(() => {
    window.cancelAnimationFrame(flushFrameRef.current ?? 0);
    flushFrameRef.current = undefined;
    const lines = pendingLinesRef.current;
    pendingLinesRef.current = [];
    if (lines.length > 0) store.appendLmnOutputLines(lines);
  }, [store]);

  const queueLine = useCallback(
    (line: string) => {
      pendingLinesRef.current.push(line);
      flushFrameRef.current ??= window.requestAnimationFrame(flushLines);
    },
    [flushLines],
  );

  const stopFollowing = useCallback(() => {
    flushLines();
    followingRef.current = false;
    streamReadyRef.current = false;
    generationRef.current += 1;
    window.clearInterval(statusTimerRef.current);
    window.clearTimeout(reconnectTimerRef.current);
    window.clearTimeout(finishTimerRef.current);
    finishTimerRef.current = undefined;
    wsRef.current?.close();
  }, [flushLines]);

  // Only the job status of the server ends a run here; a lost output stream is reconnected.
  const finish = useCallback(
    (status: 'completed' | 'failed') => {
      stopFollowing();
      setConnection('connected');
      store.setLmnPlaybookStatus(status);
    },
    [stopFollowing, store],
  );

  const resetOutput = useCallback(() => {
    window.cancelAnimationFrame(flushFrameRef.current ?? 0);
    flushFrameRef.current = undefined;
    pendingLinesRef.current = [];
    outputPositionRef.current = 0;
    outputJobRef.current = null;
    store.clearLmnOutput();
  }, [store]);

  const handleMessage = useCallback(
    (msg: LmnOutputMessage) => {
      // The server numbers the run's messages; others leave the position as it is.
      if (typeof msg.seq === 'number') outputPositionRef.current = msg.seq + 1;
      if (msg.job_id) outputJobRef.current = msg.job_id;
      if (msg.type === 'stdout' || msg.type === 'stderr' || msg.type === 'event') {
        queueLine(msg.data);
      } else if (msg.type === 'status') {
        if (msg.data === 'successful' || msg.data === 'completed') {
          finish('completed');
        } else if (msg.data === 'failed') {
          finish('failed');
        }
      }
    },
    [finish, queueLine],
  );

  const connectOutput = useCallback(() => {
    window.clearTimeout(reconnectTimerRef.current);
    wsRef.current?.close();
    const ws = createLmnWebSocket();
    wsRef.current = ws;

    ws.onmessage = (event) => {
      lastContactRef.current = Date.now();
      let msg: LmnOutputMessage;
      try {
        msg = JSON.parse(event.data as string) as LmnOutputMessage;
      } catch {
        msg = { type: 'stdout', data: event.data as string };
      }
      if (msg.type === 'position') {
        // The replay of the run so far follows, from this position on.
        streamReadyRef.current = true;
        streamEpochRef.current += 1;
        reconnectAttemptRef.current = 0;
        setConnection('connected');
        setFollowingOverHttp(false);
        resetOutput();
        outputPositionRef.current = Number(msg.data) || 0;
        outputJobRef.current = msg.job_id ?? null;
        return;
      }
      handleMessage(msg);
    };

    ws.onclose = () => {
      if (wsRef.current !== ws) return;
      streamReadyRef.current = false;
      if (!followingRef.current) return;
      setConnection((current) => (current === 'unresponsive' ? current : 'reconnecting'));
      const delay = Math.min(1000 * 2 ** reconnectAttemptRef.current, MAX_RECONNECT_DELAY_MS);
      reconnectAttemptRef.current += 1;
      reconnectTimerRef.current = window.setTimeout(() => connectOutputRef.current(), delay);
    };
  }, [handleMessage, resetOutput]);
  connectOutputRef.current = connectOutput;

  // The stream replays the run up to its final status, which ends it here with the whole log;
  // the status alone ends it only if that replay does not come in time.
  const finishAfterReplay = useCallback(
    (status: 'completed' | 'failed') => {
      if (finishTimerRef.current !== undefined) return;
      finishTimerRef.current = window.setTimeout(() => finish(status), FINAL_REPLAY_MS);
      const state = wsRef.current?.readyState;
      if (state !== WebSocket.OPEN && state !== WebSocket.CONNECTING) {
        reconnectAttemptRef.current = 0;
        connectOutput();
      }
    },
    [connectOutput, finish],
  );

  const startPlaybook = useCallback(async (): Promise<boolean> => {
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
        lmn_local_install: currentStore.lmnLocalInstall,
        lmn_webui_port: currentStore.lmnWebuiPort,
      });
      return true;
    } catch (error) {
      // Started already, e.g. by this page before a reload: follow that run.
      if ((error as ApiError).status === 409) return true;
      store.appendLmnOutput(`${t('lmnInstall.playbookError')}: ${(error as Error).message}`);
      store.setLmnPlaybookStatus('failed');
      return false;
    }
  }, [store, t]);

  const pollStatus = useCallback(async () => {
    const generation = generationRef.current;
    pollInFlightRef.current = true;
    try {
      const { status } = await getLmnPlaybookStatus(AbortSignal.timeout(STATUS_TIMEOUT_MS));
      // The page was left or the run ended while the request was out.
      if (generation !== generationRef.current) return;
      lastContactRef.current = Date.now();
      setConnection((current) => (current === 'unresponsive' ? 'reconnecting' : current));
      if (status === 'idle' && startWhenIdleRef.current) {
        startWhenIdleRef.current = false;
        resetOutput();
        store.clearLmnFetchedConfig();
        if (!(await startPlaybook()) && generation === generationRef.current) stopFollowing();
      } else if (status === 'completed' || status === 'failed') {
        finishAfterReplay(status);
      }
    } catch {
      // Unreachable for now; the deadline in checkProgress tells when that lasts.
    } finally {
      pollInFlightRef.current = false;
    }
  }, [finishAfterReplay, resetOutput, startPlaybook, stopFollowing, store]);

  // Without the stream, e.g. behind a proxy or in a browser that does not pass WebSockets, the output comes over HTTP.
  const fetchOutput = useCallback(async (): Promise<void> => {
    const generation = generationRef.current;
    const epoch = streamEpochRef.current;
    let more = false;
    outputInFlightRef.current = true;
    try {
      const result = await getLmnOutput(outputPositionRef.current, AbortSignal.timeout(OUTPUT_TIMEOUT_MS));
      const stale = generation !== generationRef.current || epoch !== streamEpochRef.current || streamReadyRef.current;
      if (stale) return;
      lastContactRef.current = Date.now();
      setFollowingOverHttp(true);
      if (result.job_id && outputJobRef.current && result.job_id !== outputJobRef.current) {
        // Another run: its output starts over.
        resetOutput();
        more = true;
      } else {
        outputJobRef.current = result.job_id ?? outputJobRef.current;
        outputPositionRef.current = result.first;
        result.messages.forEach(handleMessage);
        more = followingRef.current && result.next < result.total;
      }
    } catch {
      // Unreachable for now; the next check tries again.
      setFollowingOverHttp(false);
    } finally {
      outputInFlightRef.current = false;
    }
    if (more) await fetchOutputRef.current();
  }, [handleMessage, resetOutput]);
  fetchOutputRef.current = fetchOutput;

  const checkProgress = useCallback(() => {
    if (!followingRef.current) return;
    if (!streamReadyRef.current && Date.now() - lastContactRef.current > UNRESPONSIVE_AFTER_MS) {
      setConnection('unresponsive');
    }
    if (!pollInFlightRef.current) void pollStatus();
    if (!streamReadyRef.current && !outputInFlightRef.current) void fetchOutput();
  }, [fetchOutput, pollStatus]);

  const followRun = useCallback(() => {
    generationRef.current += 1;
    followingRef.current = true;
    lastContactRef.current = Date.now();
    connectOutput();
    window.clearInterval(statusTimerRef.current);
    statusTimerRef.current = window.setInterval(checkProgress, STATUS_POLL_MS);
  }, [checkProgress, connectOutput]);

  const checkAgain = useCallback(async () => {
    const generation = generationRef.current;
    lastContactRef.current = Date.now();
    reconnectAttemptRef.current = 0;
    setConnection('reconnecting');
    // After a restart, the web installer knows the LMN installer only again from the access it saved.
    const host = useInstallerStore.getState().lmnSshHost;
    if (host) await checkLmnConnection(host).catch(() => null);
    if (generation !== generationRef.current) return;
    connectOutput();
    if (!pollInFlightRef.current) void pollStatus();
  }, [connectOutput, pollStatus]);

  // Auto-fetch config from LMN API as soon as playbook completes
  useEffect(() => {
    if (store.lmnPlaybookStatus !== 'completed' || configFetched || configuring) return;

    const fetchConfig = async () => {
      setConfiguring(true);
      setConfigError(null);

      try {
        const edulutionConfig = await getEdulutionConfig();
        if (!edulutionConfig.ca_certificate) throw new Error('missing CA certificate');

        const currentStore = useInstallerStore.getState();
        const lmnExternalDomain = currentStore.lmnSshHost;

        store.setConfiguration({
          lmnExternalDomain,
          lmnBinduserDn: edulutionConfig.binduser_dn,
          lmnBinduserPw: edulutionConfig.binduser_password,
          lmnLdapSchema: 'ldaps',
          lmnLdapPort: 636,
          lmnCaCertificate: edulutionConfig.ca_certificate,
        });

        // Shut down the LMN installer API to free port 8000
        void shutdownLmnInstaller().catch(() => {
          // May fail if API already terminated
        });
      } catch {
        setConfigError(t('lmnInstall.configError'));
      } finally {
        setConfiguring(false);
      }
    };

    void fetchConfig();
  }, [store.lmnPlaybookStatus, configFetched, configuring, store, t]);

  // "Next" button: submit config to webinstaller API and navigate
  const handleContinue = useCallback(async () => {
    setSubmitting(true);
    store.setEdulutionExternalDomain(edulutionExternalDomain);
    try {
      const currentStore = useInstallerStore.getState();
      await submitConfiguration({
        organizationType: currentStore.organizationType!,
        deploymentTarget: currentStore.deploymentTarget!,
        lmnExternalDomain: currentStore.lmnExternalDomain,
        lmnBinduserDn: currentStore.lmnBinduserDn,
        lmnBinduserPw: currentStore.lmnBinduserPw,
        lmnLdapSchema: currentStore.lmnLdapSchema,
        lmnLdapPort: currentStore.lmnLdapPort,
        lmnLdapHost: lmnLdapHost(currentStore),
        lmnCaCertificate: currentStore.lmnCaCertificate,
        edulutionExternalDomain,
        lmnLocalInstall: currentStore.lmnLocalInstall,
        lmnWebuiPort: currentStore.lmnWebuiPort,
      });
    } catch {
      // Store already has values, continue anyway
    } finally {
      setSubmitting(false);
    }
    void navigate('/check');
  }, [navigate, store, edulutionExternalDomain]);

  useEffect(() => {
    let active = true;
    const run = async () => {
      // Opening the page again (history, reload) must not run linuxmuster-setup a second time.
      const serverStatus = await getLmnPlaybookStatus()
        .then((result) => result.status)
        .catch(() => null);
      if (!active) return;
      // Once the installer API has been shut down after a successful run, only the store knows the result.
      const status =
        serverStatus ?? (useInstallerStore.getState().lmnPlaybookStatus === 'completed' ? 'completed' : null);
      if (status === 'completed') {
        store.setLmnPlaybookStatus('completed');
        return;
      }
      store.setLmnPlaybookStatus('running');
      if (status === null) {
        // A reload while the server is unreachable: a run may be going on. The status poll starts one if none is.
        startWhenIdleRef.current = true;
        followRun();
        return;
      }
      if (status !== 'running') {
        // A new run may target another server, so the configuration of an earlier run no longer applies.
        store.clearLmnOutput();
        store.clearLmnFetchedConfig();
      }
      // Connected after the start: the server sends the whole output of the run on connecting.
      if (status !== 'running' && !(await startPlaybook())) return;
      if (!active) return;
      followRun();
    };
    void run();
    return () => {
      active = false;
      // Leaving the page is not a lost connection.
      stopFollowing();
    };
  }, []);

  const isRunning = store.lmnPlaybookStatus === 'running';
  const isCompleted = store.lmnPlaybookStatus === 'completed';
  const isFailed = store.lmnPlaybookStatus === 'failed';
  // The playbook prints this only when linuxmuster-setup ran, and thereby replaced the host keys.
  const newSshHostKeys = store.lmnOutputLog.some((line) =>
    line.text.includes('linuxmuster-setup created new SSH host keys'),
  );

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-bold text-foreground">{t('lmnInstall.title')}</h3>

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {isRunning && (
          <>
            <FontAwesomeIcon
              icon={faSpinner}
              spin
              className="text-muted-foreground"
            />
            {t('lmnInstall.running')}
          </>
        )}
        {isCompleted && (
          <>
            <FontAwesomeIcon
              icon={faCircleCheck}
              className="text-green-500"
            />
            <span className="text-green-700">{t('lmnInstall.success')}</span>
          </>
        )}
        {isFailed && (
          <>
            <FontAwesomeIcon
              icon={faCircleXmark}
              className="text-red-500"
            />
            <span className="text-red-700">{t('lmnInstall.failed')}</span>
          </>
        )}
      </div>

      {isRunning && connection === 'reconnecting' && !followingOverHttp && (
        <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          <FontAwesomeIcon
            icon={faSpinner}
            spin
            className="mt-0.5 text-amber-500"
          />
          {t('lmnInstall.reconnecting')}
        </div>
      )}

      {isRunning && connection === 'unresponsive' && (
        <div className="flex flex-col gap-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          <div className="flex items-start gap-2">
            <FontAwesomeIcon
              icon={faTriangleExclamation}
              className="mt-0.5 text-amber-500"
            />
            <span>
              {t('lmnInstall.unresponsive', { minutes: UNRESPONSIVE_AFTER_MS / 60000 })}{' '}
              <code className="break-all">tail -f /opt/edulution-installer/ansible/artifacts/*/stdout</code>
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="btn-outline"
              size="md"
              className="justify-center"
              onClick={() => {
                void checkAgain();
              }}
            >
              {t('lmnInstall.checkAgain')}
            </Button>
            {/* The setup page connects to the server again; a run that is still going on is followed afterwards. */}
            <Button
              variant="btn-outline"
              size="md"
              className="justify-center"
              onClick={() => navigate('/lmn-setup')}
            >
              {t('lmnInstall.backToSetup')}
            </Button>
          </div>
        </div>
      )}

      <div
        ref={logRef}
        className="h-72 overflow-y-auto rounded-lg bg-gray-900 p-3 font-mono text-xs text-green-400"
      >
        {store.lmnOutputLog.map((line) => (
          <div
            key={line.id}
            className={`whitespace-pre-wrap ${line.text.includes('[ERROR]') || line.text.includes('FAILED') ? 'text-red-400' : ''}`}
          >
            {line.text}
          </div>
        ))}
        {isRunning && <div className="animate-pulse text-muted-foreground">_</div>}
      </div>

      {isCompleted && (
        <>
          {configuring && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FontAwesomeIcon
                icon={faSpinner}
                spin
                className="text-muted-foreground"
              />
              {t('lmnInstall.configuringEdulution')}
            </div>
          )}
          {configError && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{configError}</div>}
          {configFetched && (
            <>
              <div className="flex items-center gap-2 rounded-lg bg-green-50 p-3 text-sm text-green-800">
                <FontAwesomeIcon
                  icon={faCircleCheck}
                  className="text-green-500"
                />
                {t(store.lmnLocalInstall ? 'lmnInstall.configFetchedLocal' : 'lmnInstall.configFetched')}
              </div>
              {/* On the same machine a restart now would stop the installer script; it recommends one at its end. */}
              {!store.lmnLocalInstall && (
                <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                  <FontAwesomeIcon
                    icon={faTriangleExclamation}
                    className="mt-0.5 text-amber-500"
                  />
                  {t('lmnInstall.restartHint')}
                </div>
              )}
              {newSshHostKeys && (
                <div className="flex items-start gap-2 rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
                  <FontAwesomeIcon
                    icon={faCircleInfo}
                    className="mt-0.5 text-blue-500"
                  />
                  {t('lmnInstall.sshHostKeyHint')}
                </div>
              )}
              <EdulutionDomainField
                value={edulutionExternalDomain}
                onChange={setEdulutionExternalDomain}
              />
              <Button
                variant="btn-security"
                size="lg"
                className="w-full justify-center text-white"
                onClick={() => {
                  void handleContinue();
                }}
                disabled={submitting || !isValidEdulutionDomain(edulutionExternalDomain)}
              >
                {submitting ? t('lmnInstall.configuringEdulution') : t('common.next')}
              </Button>
            </>
          )}
        </>
      )}

      {isFailed && (
        <Button
          variant="btn-outline"
          size="lg"
          className="w-full justify-center"
          onClick={() => navigate('/lmn-setup')}
        >
          {t('lmnInstall.backToSetup')}
        </Button>
      )}
    </div>
  );
};

export default LmnInstallPage;
