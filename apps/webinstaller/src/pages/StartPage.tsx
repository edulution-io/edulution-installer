import { useNavigate } from 'react-router-dom';
import { Button } from '@edulution-io/ui-kit';

const StartPage = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center gap-6">
      <h2 className="text-2xl font-bold text-gray-800">Herzlich Willkommen!</h2>
      <p className="text-center text-gray-600">
        Dieser Assistent führt Sie durch die Installation und Konfiguration der edulution UI.
      </p>
      <Button
        variant="btn-security"
        size="lg"
        className="w-full justify-center text-white"
        onClick={() => navigate('/organization')}
      >
        Installation starten
      </Button>
    </div>
  );
};

export default StartPage;
