import { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@edulution-io/ui-kit';
import { startInstallation, shutdownInstaller } from '../api/installerApi';
import useInstallerStore from '../store/useInstallerStore';

const POLL_START_DELAY_MS = 30000;
const POLL_INTERVAL_MS = 5000;
const REDIRECT_FALLBACK_MS = 120000;

const FinishPage = () => {
  const [started, setStarted] = useState(false);
  const [showManualLink, setShowManualLink] = useState(false);
  const { t } = useTranslation();
  const redirectedRef = useRef(false);

  const edulutionDomain = useInstallerStore((s) => s.edulutionExternalDomain);
  const edulutionUrl = `https://${edulutionDomain || window.location.hostname}`;

  const redirect = () => {
    if (redirectedRef.current) return;
    redirectedRef.current = true;
    window.location.href = edulutionUrl;
  };

  useEffect(() => {
    if (started) return;
    setStarted(true);

    const run = async () => {
      try {
        await startInstallation();
      } catch {
        // Errors may occur if backend processes the request asynchronously
      }

      // Files are written synchronously by /api/finish, trigger shutdown immediately
      void shutdownInstaller().catch(() => {
        // Shutdown may fail if server already terminated
      });
    };
    void run();
  }, [started]);

  useEffect(() => {
    // Poll the edulution health endpoint until it responds
    const pollTimeout = setTimeout(() => {
      const interval = setInterval(async () => {
        try {
          const response = await fetch(edulutionUrl);
          if (response.ok) {
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

  return (
    <div className="flex flex-col items-center gap-6">
      <h3 className="text-lg font-bold text-gray-800">{t('finish.title')}</h3>
      <FontAwesomeIcon
        icon={faSpinner}
        spin
        className="text-4xl text-gray-500"
      />
      <p className="text-center text-gray-600">{t('finish.installing')}</p>
      <p className="text-center text-sm text-gray-500">
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
