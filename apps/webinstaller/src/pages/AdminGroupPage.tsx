import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@edulution-io/ui-kit';
import { Input } from '@shared-ui';
import useInstallerStore from '../store/useInstallerStore';
import { submitAdminGroup } from '../api/installerApi';

const AdminGroupPage = () => {
  const navigate = useNavigate();
  const { deploymentTarget, initialAdminGroup, setInitialAdminGroup } = useInstallerStore();

  const [adminGroup, setAdminGroup] = useState(initialAdminGroup);
  const [submitting, setSubmitting] = useState(false);

  const isGeneric = deploymentTarget === 'generic';
  const isValid = !isGeneric || adminGroup.trim() !== '';

  const handleSubmit = useCallback(async () => {
    if (!isValid) return;
    setSubmitting(true);
    setInitialAdminGroup(adminGroup);
    await submitAdminGroup(adminGroup);
    setSubmitting(false);
    void navigate('/certificate');
  }, [isValid, adminGroup, setInitialAdminGroup, navigate]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <label
          htmlFor="set_admin_group"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          Optional: Hier kann eine initiale Admin-Gruppe für edulution definiert werden.
        </label>
        <Input
          id="set_admin_group"
          variant="login"
          placeholder="z.B. Verwaltung, role-admins, etc."
          value={adminGroup}
          onChange={(e) => setAdminGroup(e.target.value)}
        />
        <p className="mt-2 text-sm text-gray-600">
          Bei linuxmuster.net-Installationen ist &quot;role-globaladministrator&quot; standardmäßig aktiviert. Die hier
          definierte Gruppe hat nur erweiterte Rechte innerhalb von edulution.
        </p>
        {isGeneric && !adminGroup.trim() && (
          <p className="mt-1 text-sm font-bold text-red-600">
            Bei Unternehmens-Installationen muss eine Admin-Gruppe angegeben werden!
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
        Weiter
      </Button>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate('/token')}
      >
        Abbrechen
      </Button>
    </div>
  );
};

export default AdminGroupPage;
