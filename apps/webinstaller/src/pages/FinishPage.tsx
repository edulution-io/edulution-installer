import { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner, faCircleXmark } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@edulution-io/ui-kit';
import { startInstallation } from '../api/installerApi';
import type { ApiError } from '../api/installerApi';
import useInstallerStore from '../store/useInstallerStore';

const POLL_START_DELAY_MS = 30000;
const POLL_INTERVAL_MS = 10000;
const REDIRECT_FALLBACK_MS = 600000;

const FinishPage = () => {
  const [started, setStarted] = useState(false);
  const [showManualLink, setShowManualLink] = useState(false);
  const [error, setError] = useState('');
  const { t } = useTranslation();
  const redirectedRef = useRef(false);
  // After a refused finish there is no edulution to wait for or go to.
  const failedRef = useRef(false);

  const edulutionDomain = useInstallerStore((s) => s.edulutionExternalDomain);
  const resetStore = useInstallerStore((s) => s.reset);
  const edulutionUrl = `https://${edulutionDomain || window.location.hostname}`;

  const fail = (message: string) => {
    failedRef.current = true;
    setError(message);
  };

  const redirect = () => {
    if (redirectedRef.current || failedRef.current) return;
    redirectedRef.current = true;
    resetStore();
    window.location.href = edulutionUrl;
  };

  useEffect(() => {
    if (started) return;
    setStarted(true);

    const run = async () => {
      // The installer script removes the web installer once the configuration is written.
      try {
        const response = await startInstallation();
        if (!response.status) fail(response.message);
      } catch (err) {
        // An answer with an error status is a definite failure. A lost connection may follow a finish
        // that went through, as the script removes the web installer then; the page keeps waiting.
        const { status } = err as Partial<ApiError>;
        if (status) fail(t('finish.serverError', { status }));
      }
    };
    void run();
  }, [started]);

  useEffect(() => {
    // Poll the edu-api health endpoint until it responds
    const healthUrl = `${edulutionUrl}/edu-api/health/check`;
    const pollTimeout = setTimeout(() => {
      const interval = setInterval(async () => {
        if (failedRef.current) {
          clearInterval(interval);
          return;
        }
        try {
          const response = await fetch(healthUrl);
          // 503 = traefik not ready, 502 = api not ready, 401 = api running (auth required). Only as JSON:
          // on the same host, the web installer itself answers 200 (its page) or 401 (without a session).
          const fromApi =
            (response.status === 401 || response.ok) && response.headers.get('content-type')?.includes('json');
          if (fromApi) {
            clearInterval(interval);
            redirect();
          }
        } catch {
          // Not ready yet - SSL cert mismatch, network error, or server not up
        }
      }, POLL_INTERVAL_MS);

      return () => clearInterval(interval);
    }, POLL_START_DELAY_MS);

    // Fallback redirect after timeout (handles SSL cert changes where fetch always fails)
    const fallbackTimeout = setTimeout(() => {
      redirect();
    }, REDIRECT_FALLBACK_MS);

    // Show manual button after 30s
    const linkTimeout = setTimeout(() => {
      setShowManualLink(true);
    }, POLL_START_DELAY_MS);

    return () => {
      clearTimeout(pollTimeout);
      clearTimeout(fallbackTimeout);
      clearTimeout(linkTimeout);
    };
  }, []);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-6">
        <h3 className="text-lg font-bold text-foreground">{t('finish.failed')}</h3>
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800">
          <FontAwesomeIcon
            icon={faCircleXmark}
            className="text-red-500"
          />
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-6">
      <h3 className="text-lg font-bold text-foreground">{t('finish.title')}</h3>
      <FontAwesomeIcon
        icon={faSpinner}
        spin
        className="text-4xl text-muted-foreground"
      />
      <p className="text-center text-muted-foreground">{t('finish.installing')}</p>
      <p className="text-center text-sm text-muted-foreground">
        {t('finish.redirect')}
      </p>
      {showManualLink && (
        <Button
          variant="btn-security"
          size="lg"
          className="w-full justify-center text-white"
          onClick={redirect}
        >
          {t('finish.openEdulution')}
        </Button>
      )}
    </div>
  );
};

export default FinishPage;
