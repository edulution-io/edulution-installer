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

const App = () => {
  const { t } = useTranslation();

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
                src="/img/edulution.io_INSTALLER.svg"
                alt="edulution.io Logo"
                className="logo"
              />
            </a>
          </div>

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
            <LanguageSwitcher />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default App;
