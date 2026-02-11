import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@edulution-io/ui-kit';
import useInstallerStore from '../store/useInstallerStore';
import { checkProxy } from '../api/installerApi';
import CertificateForm from '../components/CertificateForm';

const CertificatePage = () => {
  const navigate = useNavigate();
  const { certificateConfigured, proxyDetected, setProxyDetected, deploymentTarget } = useInstallerStore();
  const nextPage = deploymentTarget === 'linuxmuster' ? '/lmn-setup' : '/finish';
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
        <p className="text-gray-600">Prüfe Netzwerk-Konfiguration...</p>
      </div>
    );
  }

  if (proxyDetected) {
    return (
      <div className="flex flex-col gap-4">
        <h3 className="text-lg font-bold text-gray-800">Zertifikat</h3>
        <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-800">
          Du verwendest einen Reverse-Proxy. Daher kann für edulution kein gültiges Zertifikat hinterlegt / ausgestellt
          werden.
        </div>
        <Button
          variant="btn-security"
          size="lg"
          className="w-full justify-center text-white"
          onClick={() => navigate(nextPage)}
        >
          Installation starten
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-bold text-gray-800">Zertifikat</h3>

      <CertificateForm />

      <Button
        variant="btn-security"
        size="lg"
        className="mt-2 w-full justify-center text-white"
        onClick={() => navigate(nextPage)}
        disabled={!certificateConfigured}
      >
        Installation starten
      </Button>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate('/admin-group')}
      >
        Zurück
      </Button>
    </div>
  );
};

export default CertificatePage;
