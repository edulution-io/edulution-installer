import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@edulution-io/ui-kit';
import useInstallerStore from '../store/useInstallerStore';
import { checkProxy } from '../api/installerApi';
import CertificateForm from '../components/CertificateForm';

const CertificatePage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { certificateConfigured, proxyDetected, setProxyDetected, adType } = useInstallerStore();
  const nextPage = '/finish';
  const backPage = adType === 'new' ? '/lmn-install' : '/admin-group';
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const detectProxy = async () => {
      try {
        const result = await checkProxy();
        setProxyDetected(result.proxyDetected);
      } catch {
        setProxyDetected(false);
      }
      setLoading(false);
    };
    void detectProxy();
  }, [setProxyDetected]);

  if (loading) {
    return (
      <div className="flex flex-col items-center gap-4">
        <p className="text-gray-600">{t('certificate.checkingNetwork')}</p>
      </div>
    );
  }

  if (proxyDetected) {
    return (
      <div className="flex flex-col gap-4">
        <h3 className="text-lg font-bold text-gray-800">{t('certificate.title')}</h3>
        <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-800">
          {t('certificate.proxyWarning')}
        </div>
        <Button
          variant="btn-security"
          size="lg"
          className="w-full justify-center text-white"
          onClick={() => navigate(nextPage)}
        >
          {t('common.startInstallation')}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-bold text-gray-800">{t('certificate.title')}</h3>

      <CertificateForm />

      <Button
        variant="btn-security"
        size="lg"
        className="mt-2 w-full justify-center text-white"
        onClick={() => navigate(nextPage)}
        disabled={!certificateConfigured}
      >
        {t('common.startInstallation')}
      </Button>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate(nextPage)}
      >
        {t('common.skip')}
      </Button>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate(backPage)}
      >
        {t('common.back')}
      </Button>
    </div>
  );
};

export default CertificatePage;
