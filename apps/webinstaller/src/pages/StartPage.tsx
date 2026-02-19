import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@edulution-io/ui-kit';

const StartPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center gap-6">
      <h2 className="text-2xl font-bold text-gray-800">{t('start.welcome')}</h2>
      <p className="text-center text-gray-600">
        {t('start.description')}
      </p>
      <Button
        variant="btn-security"
        size="lg"
        className="w-full justify-center text-white"
        onClick={() => navigate('/organization')}
      >
        {t('start.startButton')}
      </Button>
    </div>
  );
};

export default StartPage;
