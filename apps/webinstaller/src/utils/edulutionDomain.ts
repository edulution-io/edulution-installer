// Normalised like location.hostname, so that IPv6 forms and a trailing dot are compared correctly.
const normalizedHost = (value: string) => {
  const host = value.trim();
  const literal = host.includes(':') && !host.startsWith('[') ? `[${host}]` : host;
  try {
    return new URL(`http://${literal}`).hostname.replace(/\.$/, '');
  } catch {
    return host.toLowerCase();
  }
};

// Clients cannot reach the server under a loopback name, so it must not become the edulution address.
export const isLoopbackHost = (value: string) => {
  const name = normalizedHost(value);
  return (
    name === 'localhost' ||
    name.endsWith('.localhost') ||
    /^127(\.\d+){3}$/.test(name) ||
    name === '0.0.0.0' ||
    name === '[::1]' ||
    name === '[::]' ||
    name.startsWith('[::ffff:7f')
  );
};

export const isValidEdulutionDomain = (host: string) => host.trim() !== '' && !isLoopbackHost(host);

export const defaultEdulutionDomain = () => (isLoopbackHost(window.location.hostname) ? '' : window.location.hostname);
