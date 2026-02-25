import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@edulution-io/ui-kit';
import { Input } from '@shared-ui';
import useInstallerStore from '../store/useInstallerStore';
import { submitConfiguration } from '../api/installerApi';

const ConfigurePage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const store = useInstallerStore();

  const [lmnExternalDomain, setLmnExternalDomain] = useState(store.lmnExternalDomain);
  const [lmnBinduserDn, setLmnBinduserDn] = useState(store.lmnBinduserDn);
  const [lmnBinduserPw, setLmnBinduserPw] = useState(store.lmnBinduserPw);
  const [lmnLdapSchema, setLmnLdapSchema] = useState<'ldap' | 'ldaps'>(store.lmnLdapSchema);
  const [lmnLdapPort, setLmnLdapPort] = useState(store.lmnLdapPort);
  const [edulutionExternalDomain, setEdulutionExternalDomain] = useState(store.edulutionExternalDomain);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!edulutionExternalDomain) {
      setEdulutionExternalDomain(window.location.hostname);
    }
  }, [edulutionExternalDomain]);

  const handleSchemaChange = useCallback(
    (value: string) => {
      const schema = value as 'ldap' | 'ldaps';
      setLmnLdapSchema(schema);
      if (schema === 'ldap' && lmnLdapPort === 636) {
        setLmnLdapPort(389);
      }
      if (schema === 'ldaps' && lmnLdapPort === 389) {
        setLmnLdapPort(636);
      }
    },
    [lmnLdapPort],
  );

  const isValid =
    lmnExternalDomain.trim() !== '' &&
    lmnBinduserDn.trim() !== '' &&
    lmnBinduserPw.trim() !== '' &&
    lmnLdapPort > 0 &&
    lmnLdapPort <= 65535 &&
    edulutionExternalDomain.trim() !== '';

  const handleSubmit = useCallback(async () => {
    if (!isValid || !store.deploymentTarget || !store.organizationType) return;
    setSubmitting(true);

    store.setConfiguration({
      lmnExternalDomain,
      lmnBinduserDn,
      lmnBinduserPw,
      lmnLdapSchema,
      lmnLdapPort,
      edulutionExternalDomain,
    });

    await submitConfiguration({
      organizationType: store.organizationType,
      deploymentTarget: store.deploymentTarget,
      lmnExternalDomain,
      lmnBinduserDn,
      lmnBinduserPw,
      lmnLdapSchema,
      lmnLdapPort,
      edulutionExternalDomain,
    });

    setSubmitting(false);
    void navigate('/check');
  }, [
    isValid,
    store,
    lmnExternalDomain,
    lmnBinduserDn,
    lmnBinduserPw,
    lmnLdapSchema,
    lmnLdapPort,
    edulutionExternalDomain,
    navigate,
  ]);

  return (
    <div className="flex flex-col gap-4">
      <div>
        <label
          htmlFor="lmn_external_domain"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          {store.deploymentTarget === 'linuxmuster'
            ? t('configure.externalDomainLmn')
            : t('configure.externalDomainGeneric')}
        </label>
        <Input
          id="lmn_external_domain"
          variant="login"
          value={lmnExternalDomain}
          onChange={(e) => setLmnExternalDomain(e.target.value)}
          className={lmnExternalDomain.trim() ? 'valid-input' : ''}
        />
      </div>

      <div>
        <label
          htmlFor="lmn_binduser_dn"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          {t('configure.ldapUser')}
        </label>
        <Input
          id="lmn_binduser_dn"
          variant="login"
          value={lmnBinduserDn}
          onChange={(e) => setLmnBinduserDn(e.target.value)}
          className={lmnBinduserDn.trim() ? 'valid-input' : ''}
        />
      </div>

      <div>
        <label
          htmlFor="lmn_binduser_pw"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          {t('configure.ldapPassword')}
        </label>
        <Input
          id="lmn_binduser_pw"
          variant="login"
          type="text"
          value={lmnBinduserPw}
          onChange={(e) => setLmnBinduserPw(e.target.value)}
          className={lmnBinduserPw.trim() ? 'valid-input' : ''}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label
            htmlFor="lmn_ldap_schema"
            className="mb-1 block text-sm font-bold text-gray-800"
          >
            {t('configure.ldapSchema')}
          </label>
          <select
            id="lmn_ldap_schema"
            value={lmnLdapSchema}
            onChange={(e) => handleSchemaChange(e.target.value)}
            className={`w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm ${lmnLdapSchema ? 'valid-input' : ''}`}
          >
            <option value="ldap">ldap://</option>
            <option value="ldaps">ldaps://</option>
          </select>
        </div>

        <div>
          <label
            htmlFor="lmn_ldap_port"
            className="mb-1 block text-sm font-bold text-gray-800"
          >
            {t('configure.ldapPort')}
          </label>
          <Input
            id="lmn_ldap_port"
            variant="login"
            type="number"
            min={1}
            max={65535}
            value={lmnLdapPort}
            onChange={(e) => setLmnLdapPort(Number(e.target.value))}
            className={lmnLdapPort > 0 ? 'valid-input' : ''}
          />
        </div>
      </div>

      <div>
        <label
          htmlFor="edulutionui_external_domain"
          className="mb-1 block text-sm font-bold text-gray-800"
        >
          {t('configure.externalDomainEdulution')}
        </label>
        <Input
          id="edulutionui_external_domain"
          variant="login"
          value={edulutionExternalDomain}
          onChange={(e) => setEdulutionExternalDomain(e.target.value)}
          className={edulutionExternalDomain.trim() ? 'valid-input' : ''}
        />
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
        {submitting ? t('configure.verifying') : t('common.verify')}
      </Button>

      <Button
        variant="btn-outline"
        size="lg"
        className="w-full justify-center"
        onClick={() => navigate('/token')}
      >
        {t('common.back')}
      </Button>
    </div>
  );
};

export default ConfigurePage;
