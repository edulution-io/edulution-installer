import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@edulution-io/ui-kit';
import { Input } from '@shared-ui';
import useInstallerStore from '../store/useInstallerStore';
import { submitAdminGroup } from '../api/installerApi';

const AdminGroupPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { deploymentTarget, initialAdminGroup, setInitialAdminGroup, adType } = useInstallerStore();

  const [adminGroup, setAdminGroup] = useState(initialAdminGroup);
  const [submitting, setSubmitting] = useState(false);

  const isGeneric = deploymentTarget === 'generic';
  const isValid = !isGeneric || adminGroup.trim() !== '';

  const handleSubmit = useCallback(async () => {
    if (!isValid) return;
    setSubmitting(true);
    setInitialAdminGroup(adminGroup);
    try {
      await submitAdminGroup(adminGroup);
    } catch {
      // Continue even if API call fails - admin group is optional
    } finally {
      setSubmitting(false);
    }
    void navigate('/certificate');
  }, [isValid, adminGroup, setInitialAdminGroup, navigate]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <label
          htmlFor="set_admin_group"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          {t('adminGroup.label')}
        </label>
        <Input
          id="set_admin_group"
          variant="login"
          placeholder={t('adminGroup.placeholder')}
          value={adminGroup}
          onChange={(e) => setAdminGroup(e.target.value)}
        />
        <p className="mt-2 text-sm text-gray-600">
          {t('adminGroup.hint')}
        </p>
        {isGeneric && !adminGroup.trim() && (
          <p className="mt-1 text-sm font-bold text-red-600">
            {t('adminGroup.requiredError')}
          </p>
        )}
      </div>

      <Button
        variant="btn-security"
        size="lg"
        className="mt-2 w-full justify-center text-white"
        onClick={() => {
          void handleSubmit();
        }}
        disabled={!isValid || submitting}
      >
        {t('common.next')}
      </Button>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate(adType === 'new' ? '/check' : '/token')}
      >
        {t('common.cancel')}
      </Button>
    </div>
  );
};

export default AdminGroupPage;
