// Parsed like location.hostname, so that IPv6 forms and a trailing dot are compared correctly.
// The address becomes https://<address>/, so a port, scheme or path makes it invalid (null).
const parseHost = (value: string) => {
  const host = value.trim();
  const literal = host.includes(':') && !host.startsWith('[') ? `[${host}]` : host;
  try {
    const url = new URL(`http://${literal}`);
    if (url.port || url.username || url.pathname !== '/' || url.search || url.hash) return null;
    const name = url.hostname.replace(/\.$/, '');
    // A numeric last label is read as IPv4 (127.1, 2130706433), so only the usual form passes, as in the API.
    const typed = host.toLowerCase().replace(/\.$/, '');
    if (/^(0x[0-9a-f]*|\d+)$/.test(typed.split('.').pop() ?? '') && typed !== name) return null;
    return name;
  } catch {
    return null;
  }
};

// Clients cannot reach the server under a loopback name, so it must not become the edulution address.
const isLoopbackName = (name: string) =>
  name === 'localhost' ||
  name.endsWith('.localhost') ||
  /^127(\.\d+){3}$/.test(name) ||
  name === '0.0.0.0' ||
  name === '[::1]' ||
  name === '[::]' ||
  name.startsWith('[::ffff:7f');

export type EdulutionDomainError = 'loopback' | 'invalid';

export const edulutionDomainError = (value: string): EdulutionDomainError | null => {
  if (value.trim() === '') return null;
  const name = parseHost(value);
  if (name === null) return 'invalid';
  return isLoopbackName(name) ? 'loopback' : null;
};

export const isValidEdulutionDomain = (value: string) => value.trim() !== '' && edulutionDomainError(value) === null;

export const defaultEdulutionDomain = () =>
  edulutionDomainError(window.location.hostname) ? '' : window.location.hostname;
