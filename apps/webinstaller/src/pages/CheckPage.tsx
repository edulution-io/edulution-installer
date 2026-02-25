import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@edulution-io/ui-kit';
import useInstallerStore from '../store/useInstallerStore';
import { checkApiStatus, checkWebDavStatus, checkLdapStatus, checkLdapAccessStatus } from '../api/installerApi';
import StatusCard from '../components/StatusCard';

type CheckKey = 'api' | 'webdav' | 'ldap' | 'ldapAccess';

const CheckPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { checks, setCheckResult, resetChecks } = useInstallerStore();

  const [loading, setLoading] = useState<Record<CheckKey, boolean>>({
    api: false,
    webdav: false,
    ldap: false,
    ldapAccess: false,
  });

  const runCheck = useCallback(
    async (key: CheckKey, checkFn: () => Promise<{ status: boolean; message: string }>) => {
      setLoading((prev) => ({ ...prev, [key]: true }));
      try {
        const result = await checkFn();
        setCheckResult(key, result);
      } catch {
        setCheckResult(key, { status: false, message: t('check.connectionError') });
      }
      setLoading((prev) => ({ ...prev, [key]: false }));
    },
    [setCheckResult],
  );

  const runAllChecks = useCallback(() => {
    resetChecks();
    void runCheck('api', checkApiStatus);
    void runCheck('webdav', checkWebDavStatus);
    void runCheck('ldap', checkLdapStatus);
    void runCheck('ldapAccess', checkLdapAccessStatus);
  }, [resetChecks, runCheck]);

  useEffect(() => {
    runAllChecks();
  }, []);

  const allPassed =
    checks.api?.status === true &&
    checks.webdav?.status === true &&
    checks.ldap?.status === true &&
    checks.ldapAccess?.status === true;

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-bold text-gray-800">{t('check.title')}</h3>

      <div className="flex flex-col gap-2">
        <StatusCard
          label={t('check.checkApi')}
          status={checks.api}
          loading={loading.api}
          onRetry={() => { void runCheck('api', checkApiStatus); }}
        />
        <StatusCard
          label={t('check.checkWebDav')}
          status={checks.webdav}
          loading={loading.webdav}
          onRetry={() => { void runCheck('webdav', checkWebDavStatus); }}
        />
        <StatusCard
          label={t('check.checkLdap')}
          status={checks.ldap}
          loading={loading.ldap}
          onRetry={() => { void runCheck('ldap', checkLdapStatus); }}
        />
        <StatusCard
          label={t('check.checkLdapAccess')}
          status={checks.ldapAccess}
          loading={loading.ldapAccess}
          onRetry={() => { void runCheck('ldapAccess', checkLdapAccessStatus); }}
        />
      </div>

      <Button
        variant="btn-security"
        size="lg"
        className="mt-2 w-full justify-center text-white"
        onClick={() => navigate('/admin-group')}
        disabled={!allPassed}
      >
        {t('common.next')}
      </Button>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate('/configure')}
      >
        {t('common.back')}
      </Button>
    </div>
  );
};

export default CheckPage;
