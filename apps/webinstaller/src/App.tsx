import { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '@shared-ui';
import StartPage from './pages/StartPage';
import OrganizationPage from './pages/OrganizationPage';
import TokenPage from './pages/TokenPage';
import ConfigurePage from './pages/ConfigurePage';
import CheckPage from './pages/CheckPage';
import AdminGroupPage from './pages/AdminGroupPage';
import CertificatePage from './pages/CertificatePage';
import LmnSetupPage from './pages/LmnSetupPage';
import LmnConfigPage from './pages/LmnConfigPage';
import LmnInstallPage from './pages/LmnInstallPage';
import FinishPage from './pages/FinishPage';
import LanguageSwitcher from './components/LanguageSwitcher';
import { getEdulutionDomain, getInstallerVersion } from './api/installerApi';
import useInstallerStore from './store/useInstallerStore';

const App = () => {
  const { t } = useTranslation();
  const [version, setVersion] = useState('');
  // The pages read the prefilled address when they mount, so they wait for it.
  const [domainLoaded, setDomainLoaded] = useState(false);

  useEffect(() => {
    getInstallerVersion()
      .then((result) => setVersion(result.version))
      .catch(() => {});
    getEdulutionDomain()
      .then(({ domain }) => {
        const store = useInstallerStore.getState();
        if (domain && !store.edulutionExternalDomain) store.setEdulutionExternalDomain(domain);
      })
      .catch(() => {})
      .finally(() => setDomainLoaded(true));
  }, []);

  return (
    <div className="page-wrapper">
      <Card className="w-full max-w-[600px] border-4 border-white shadow-[0_20px_60px_rgba(0,0,0,0.3)]">
        <CardContent className="p-10 max-sm:p-6 max-[480px]:p-4">
          <div className="mb-8 flex justify-center">
            <a
              href="https://edulution.io"
              target="_blank"
              rel="noopener noreferrer"
            >
              <img
                src="/img/edulution.io_INSTALLER_white.svg"
                alt="edulution.io Logo"
                className="logo"
              />
            </a>
          </div>

          {domainLoaded && (
            <Routes>
              <Route
                path="/"
                element={<StartPage />}
              />
              <Route
                path="/organization"
                element={<OrganizationPage />}
              />
              <Route
                path="/token"
                element={<TokenPage />}
              />
              <Route
                path="/configure"
                element={<ConfigurePage />}
              />
              <Route
                path="/check"
                element={<CheckPage />}
              />
              <Route
                path="/admin-group"
                element={<AdminGroupPage />}
              />
              <Route
                path="/certificate"
                element={<CertificatePage />}
              />
              <Route
                path="/lmn-setup"
                element={<LmnSetupPage />}
              />
              <Route
                path="/lmn-config"
                element={<LmnConfigPage />}
              />
              <Route
                path="/lmn-install"
                element={<LmnInstallPage />}
              />
              <Route
                path="/finish"
                element={<FinishPage />}
              />
              <Route
                path="*"
                element={<Navigate to="/" />}
              />
            </Routes>
          )}

          <div className="footer-section">
            {t('footer.infoText')}{' '}
            <a
              href="https://edulution.io"
              target="_blank"
              rel="noopener noreferrer"
            >
              edulution.io
            </a>{' '}
            {t('footer.orInThe')}{' '}
            <a
              href="https://docs.edulution.io"
              target="_blank"
              rel="noopener noreferrer"
            >
              {t('footer.documentation')}
            </a>
            <p className="mt-2">
              <a
                href="https://docs.edulution.io/docs/edulution-plattform/installation/einrichtung/"
                target="_blank"
                rel="noopener noreferrer"
              >
                {t('footer.installationGuide')}
              </a>
            </p>
            <LanguageSwitcher />
            {version && <p className="mt-2 text-xs">{t('footer.version', { version })}</p>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default App;
