import { Routes, Route, Navigate } from 'react-router-dom';
import StartPage from './pages/StartPage';
import TokenPage from './pages/TokenPage';
import ConfigurePage from './pages/ConfigurePage';
import CheckPage from './pages/CheckPage';
import AdminGroupPage from './pages/AdminGroupPage';
import CertificatePage from './pages/CertificatePage';
import FinishPage from './pages/FinishPage';

const App = () => (
  <div className="page-wrapper">
    <div className="installer-container">
      <div className="mb-8 flex justify-center">
        <a
          href="https://edulution.io"
          target="_blank"
          rel="noopener noreferrer"
        >
          <img
            src="/img/edulution.io_USER_INTERFACE.svg"
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
          path="/finish"
          element={<FinishPage />}
        />
        <Route
          path="*"
          element={<Navigate to="/" />}
        />
      </Routes>

      <div className="footer-section">
        Alle Informationen auf{' '}
        <a
          href="https://edulution.io"
          target="_blank"
          rel="noopener noreferrer"
        >
          edulution.io
        </a>{' '}
        oder in der{' '}
        <a
          href="https://docs.edulution.io"
          target="_blank"
          rel="noopener noreferrer"
        >
          Dokumentation
        </a>
      </div>
    </div>
  </div>
);

export default App;
