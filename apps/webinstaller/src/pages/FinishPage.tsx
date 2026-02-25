import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner } from '@fortawesome/free-solid-svg-icons';
import { startInstallation, shutdownInstaller } from '../api/installerApi';

const FinishPage = () => {
  const [started, setStarted] = useState(false);
  const { t } = useTranslation();

  useEffect(() => {
    if (started) return;
    setStarted(true);

    const run = async () => {
      try {
        await startInstallation();
      } catch {
        // Errors may occur if backend processes the request asynchronously
      }

      // Give the backend time to write files, then trigger shutdown
      setTimeout(() => {
        void shutdownInstaller().catch(() => {
          // Shutdown may fail if server already terminated
        });
      }, 10000);
    };
    void run();
  }, [started]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      const interval = setInterval(async () => {
        try {
          const response = await fetch(`https://${window.location.hostname}`);
          if (response.ok) {
            clearInterval(interval);
            window.location.href = `https://${window.location.hostname}`;
          }
        } catch {
          // UI not ready yet
        }
      }, 3000);

      return () => clearInterval(interval);
    }, 30000);

    return () => clearTimeout(timeout);
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
    </div>
  );
};

export default FinishPage;
