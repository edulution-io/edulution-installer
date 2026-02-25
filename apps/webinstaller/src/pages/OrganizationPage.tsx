import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSchool, faBuilding, faLandmarkDome } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@edulution-io/ui-kit';
import { Card, CardContent } from '@shared-ui';
import type { OrganizationType } from '@shared-types';
import useInstallerStore from '../store/useInstallerStore';

const OrganizationPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const store = useInstallerStore();
  const [selected, setSelected] = useState<OrganizationType>(store.organizationType ?? 'school');

  const options: { value: OrganizationType; label: string; icon: typeof faSchool }[] = [
    { value: 'school', label: t('organization.school'), icon: faSchool },
    { value: 'business', label: t('organization.business'), icon: faBuilding },
    { value: 'public-administration', label: t('organization.publicAdmin'), icon: faLandmarkDome },
  ];

  return (
    <div className="flex flex-col gap-4">
      <span className="mb-1 block text-sm font-bold text-gray-800">{t('organization.label')}</span>

      <div className="grid grid-cols-3 gap-3">
        {options.map((opt) => (
          <Card
            key={opt.value}
            variant={selected === opt.value ? 'gridSelected' : 'text'}
            className="cursor-pointer"
            onClick={() => setSelected(opt.value)}
          >
            <CardContent className="flex flex-col items-center justify-center gap-2 p-4">
              <FontAwesomeIcon
                icon={opt.icon}
                size="2x"
              />
              <span className="text-sm font-medium">{opt.label}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      <Button
        variant="btn-security"
        size="lg"
        className="mt-2 w-full justify-center text-white"
        onClick={() => {
          console.info('Selected organization type:', selected);
          store.setOrganizationType(selected);
          void navigate('/token');
        }}
      >
        {t('common.next')}
      </Button>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate('/')}
      >
        {t('common.back')}
      </Button>
    </div>
  );
};

export default OrganizationPage;
