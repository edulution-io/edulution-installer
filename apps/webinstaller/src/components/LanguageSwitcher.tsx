import { useTranslation } from 'react-i18next';

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();
  const currentLang = i18n.language?.startsWith('en') ? 'en' : 'de';

  return (
    <div className="mt-3 flex items-center justify-center gap-2">
      <button
        type="button"
        onClick={() => i18n.changeLanguage('de')}
        className={`text-2xl transition-opacity ${currentLang === 'de' ? 'opacity-100' : 'opacity-40 hover:opacity-70'}`}
        title="Deutsch"
      >
        &#127465;&#127466;
      </button>
      <button
        type="button"
        onClick={() => i18n.changeLanguage('en')}
        className={`text-2xl transition-opacity ${currentLang === 'en' ? 'opacity-100' : 'opacity-40 hover:opacity-70'}`}
        title="English"
      >
        &#127468;&#127463;
      </button>
    </div>
  );
};

export default LanguageSwitcher;
