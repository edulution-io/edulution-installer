import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@edulution-io/ui-kit';
import { Input } from '@shared-ui';
import useInstallerStore from '../store/useInstallerStore';

const validatePassword = (pw: string): string[] => {
  const errors: string[] = [];
  if (pw.length < 7) errors.push('Mindestens 7 Zeichen');
  if (!/[a-z]/.test(pw)) errors.push('Kleinbuchstaben erforderlich');
  if (!/[A-Z]/.test(pw)) errors.push('Grossbuchstaben erforderlich');
  if (!/\d/.test(pw)) errors.push('Mindestens eine Ziffer');
  if (!/[?!§+\-@#%&*()[\]{}]/.test(pw)) errors.push('Mindestens ein Sonderzeichen (?!§+-@#%&*()[]{})');
  return errors;
};

const isValidIp = (ip: string): boolean =>
  /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.test(ip) &&
  ip.split('.').every((octet) => Number(octet) <= 255);

const ipInputClass = (value: string): string => {
  if (!value) return '';
  return isValidIp(value) ? 'valid-input' : 'invalid-input';
};

const TIMEZONES = ['Europe/Berlin', 'Europe/Vienna'];

const LOCALES = ['de_DE.UTF-8', 'de_AT.UTF-8'];

const LmnConfigPage = () => {
  const navigate = useNavigate();
  const store = useInstallerStore();

  const [step, setStep] = useState(1);
  const [serverIp, setServerIp] = useState(store.lmnServerIp);
  const [netmask, setNetmask] = useState(store.lmnNetmask);
  const [gateway, setGateway] = useState(store.lmnGateway);
  const [servername, setServername] = useState(store.lmnServername);
  const [domainname, setDomainname] = useState(store.lmnDomainname);
  const [schoolname, setSchoolname] = useState(store.lmnSchoolname);
  const [location, setLocation] = useState(store.lmnLocation);
  const [country, setCountry] = useState(store.lmnCountry);
  const [state, setState] = useState(store.lmnState);
  const [dhcprange, setDhcprange] = useState(store.lmnDhcprange);
  const [adminpw, setAdminpw] = useState(store.lmnAdminpw);
  const [adminpwConfirm, setAdminpwConfirm] = useState(store.lmnAdminpw);
  const [timezone, setTimezone] = useState(store.lmnTimezone);
  const [locale, setLocale] = useState(store.lmnLocale);

  const pwErrors = useMemo(() => validatePassword(adminpw), [adminpw]);
  const pwMatch = adminpw === adminpwConfirm;

  const step1Valid =
    isValidIp(serverIp) &&
    isValidIp(netmask) &&
    isValidIp(gateway) &&
    servername.trim() !== '' &&
    domainname.trim() !== '';

  const step2Valid =
    schoolname.trim() !== '' &&
    adminpw.trim() !== '' &&
    pwErrors.length === 0 &&
    pwMatch;

  const handleSubmit = () => {
    if (!step1Valid || !step2Valid) return;

    store.setLmnConfig({
      lmnServerIp: serverIp,
      lmnNetmask: netmask,
      lmnGateway: gateway,
      lmnServername: servername,
      lmnDomainname: domainname,
      lmnSchoolname: schoolname,
      lmnLocation: location,
      lmnCountry: country,
      lmnState: state,
      lmnDhcprange: dhcprange,
      lmnAdminpw: adminpw,
      lmnTimezone: timezone,
      lmnLocale: locale,
    });

    void navigate('/lmn-install');
  };

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-bold text-gray-800">
        Linuxmuster Konfiguration (Schritt {step}/2)
      </h3>

      {step === 1 && (
        <>
          {/* Netzwerk */}
          <h4 className="text-sm font-bold text-gray-600">Netzwerk</h4>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label
                htmlFor="lmn_server_ip"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Server-IP:
              </label>
              <Input
                id="lmn_server_ip"
                variant="login"
                value={serverIp}
                onChange={(e) => setServerIp(e.target.value)}
                className={ipInputClass(serverIp)}
              />
            </div>
            <div>
              <label
                htmlFor="lmn_netmask"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Subnetzmaske:
              </label>
              <Input
                id="lmn_netmask"
                variant="login"
                value={netmask}
                onChange={(e) => setNetmask(e.target.value)}
                className={ipInputClass(netmask)}
              />
            </div>
            <div>
              <label
                htmlFor="lmn_gateway"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Gateway:
              </label>
              <Input
                id="lmn_gateway"
                variant="login"
                value={gateway}
                onChange={(e) => setGateway(e.target.value)}
                className={ipInputClass(gateway)}
              />
            </div>
          </div>

          {/* Server */}
          <h4 className="text-sm font-bold text-gray-600">Server</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="lmn_servername"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Hostname:
              </label>
              <Input
                id="lmn_servername"
                variant="login"
                value={servername}
                onChange={(e) => setServername(e.target.value)}
              />
            </div>
            <div>
              <label
                htmlFor="lmn_domainname"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Domain:
              </label>
              <Input
                id="lmn_domainname"
                variant="login"
                value={domainname}
                onChange={(e) => setDomainname(e.target.value)}
              />
            </div>
          </div>

          {/* DHCP */}
          <h4 className="text-sm font-bold text-gray-600">DHCP</h4>
          <div>
            <label
              htmlFor="lmn_dhcprange"
              className="mb-1 block text-sm font-bold text-gray-800"
            >
              DHCP-Bereich:
            </label>
            <Input
              id="lmn_dhcprange"
              variant="login"
              value={dhcprange}
              onChange={(e) => setDhcprange(e.target.value)}
            />
            <p className="mt-1 text-xs text-gray-500">Format: START-IP END-IP</p>
          </div>

          {/* System */}
          <h4 className="text-sm font-bold text-gray-600">System</h4>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label
                htmlFor="lmn_timezone"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Zeitzone:
              </label>
              <select
                id="lmn_timezone"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="w-full cursor-pointer rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm"
              >
                {TIMEZONES.map((tz) => (
                  <option
                    key={tz}
                    value={tz}
                  >
                    {tz}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="lmn_locale"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Locale:
              </label>
              <select
                id="lmn_locale"
                value={locale}
                onChange={(e) => setLocale(e.target.value)}
                className="w-full cursor-pointer rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 shadow-sm"
              >
                {LOCALES.map((loc) => (
                  <option
                    key={loc}
                    value={loc}
                  >
                    {loc}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Button
            variant="btn-security"
            size="lg"
            className="mt-2 w-full justify-center text-white"
            onClick={() => setStep(2)}
            disabled={!step1Valid}
          >
            Weiter
          </Button>

          <Button
            variant="btn-outline"
            size="lg"
            className="w-full justify-center"
            onClick={() => navigate('/lmn-setup')}
          >
            Zurück
          </Button>
        </>
      )}

      {step === 2 && (
        <>
          {/* Schule */}
          <h4 className="text-sm font-bold text-gray-600">Schule</h4>
          <div>
            <label
              htmlFor="lmn_schoolname"
              className="mb-1 block text-sm font-bold text-gray-800"
            >
              Schulname:
            </label>
            <Input
              id="lmn_schoolname"
              variant="login"
              value={schoolname}
              onChange={(e) => setSchoolname(e.target.value)}
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label
                htmlFor="lmn_location"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Ort:
              </label>
              <Input
                id="lmn_location"
                variant="login"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
            <div>
              <label
                htmlFor="lmn_country"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Land:
              </label>
              <Input
                id="lmn_country"
                variant="login"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              />
            </div>
            <div>
              <label
                htmlFor="lmn_state"
                className="mb-1 block text-sm font-bold text-gray-800"
              >
                Bundesland:
              </label>
              <Input
                id="lmn_state"
                variant="login"
                value={state}
                onChange={(e) => setState(e.target.value)}
              />
            </div>
          </div>

          {/* Admin-Passwort */}
          <h4 className="text-sm font-bold text-gray-600">Administrator-Passwort</h4>
          <div>
            <label
              htmlFor="lmn_adminpw"
              className="mb-1 block text-sm font-bold text-gray-800"
            >
              Passwort:
            </label>
            <Input
              id="lmn_adminpw"
              variant="login"
              type="password"
              value={adminpw}
              onChange={(e) => setAdminpw(e.target.value)}
            />
          </div>
          <div>
            <label
              htmlFor="lmn_adminpw_confirm"
              className="mb-1 block text-sm font-bold text-gray-800"
            >
              Passwort bestätigen:
            </label>
            <Input
              id="lmn_adminpw_confirm"
              variant="login"
              type="password"
              value={adminpwConfirm}
              onChange={(e) => setAdminpwConfirm(e.target.value)}
              className={adminpwConfirm && pwMatch && pwErrors.length === 0 ? 'valid-input' : ''}
            />
          </div>
          {adminpw && pwErrors.length > 0 && (
            <ul className="list-inside list-disc text-xs text-red-600">
              {pwErrors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          )}
          {adminpwConfirm && !pwMatch && <p className="text-xs text-red-600">Passwoerter stimmen nicht ueberein</p>}

          <Button
            variant="btn-security"
            size="lg"
            className="mt-2 w-full justify-center text-white"
            onClick={handleSubmit}
            disabled={!step2Valid}
          >
            Installation starten
          </Button>

          <Button
            variant="btn-outline"
            size="lg"
            className="w-full justify-center"
            onClick={() => setStep(1)}
          >
            Zurück
          </Button>
        </>
      )}
    </div>
  );
};

export default LmnConfigPage;
