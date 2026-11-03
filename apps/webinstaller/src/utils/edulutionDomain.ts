// Clients cannot reach the server under a loopback name, so it must not become the edulution address.
export const isLoopbackHost = (host: string) => {
  const name = host
    .trim()
    .toLowerCase()
    .replace(/^\[(.*)\]$/, '$1');
  return (
    name === 'localhost' ||
    name.endsWith('.localhost') ||
    name.startsWith('127.') ||
    name === '::1' ||
    name === '0.0.0.0'
  );
};

export const isValidEdulutionDomain = (host: string) => host.trim() !== '' && !isLoopbackHost(host);

export const defaultEdulutionDomain = () => (isLoopbackHost(window.location.hostname) ? '' : window.location.hostname);
