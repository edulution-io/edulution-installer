import { useTranslation } from 'react-i18next';
import { Input } from '@shared-ui';
import { edulutionDomainError, isValidEdulutionDomain } from '../utils/edulutionDomain';

interface EdulutionDomainFieldProps {
  value: string;
  onChange: (value: string) => void;
}

const EdulutionDomainField = ({ value, onChange }: EdulutionDomainFieldProps) => {
  const { t } = useTranslation();
  return (
    <div>
      <label
        htmlFor="edulutionui_external_domain"
        className="mb-1 block text-sm font-bold text-foreground"
      >
        {t('configure.externalDomainEdulution')}
      </label>
      <Input
        id="edulutionui_external_domain"
        variant="login"
        value={value}
        onChange={(e) => onChange(e.target.value.trim())}
        className={isValidEdulutionDomain(value) ? 'valid-input' : ''}
      />
      {edulutionDomainError(value) === 'loopback' && (
        <p className="mt-1 text-xs text-red-600">{t('configure.externalDomainLoopback')}</p>
      )}
      {edulutionDomainError(value) === 'invalid' && (
        <p className="mt-1 text-xs text-red-600">{t('configure.externalDomainInvalid')}</p>
      )}
      {!edulutionDomainError(value) && (
        <p className="mt-1 text-xs text-muted-foreground">{t('configure.externalDomainEdulutionHint')}</p>
      )}
    </div>
  );
};

export default EdulutionDomainField;
