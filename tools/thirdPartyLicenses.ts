import { readdirSync, readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import type { Plugin } from 'vite';

const OUTPUT_FILE = 'third-party-licenses.txt';
const NODE_MODULES = '/node_modules/';
const LICENCE_FILE = /^(licen[cs]e|copying|notice)/i;
// First-party: LICENSE names the terms it is included under.
const FIRST_PARTY = /^@edulution-io\//;
const RULE = '='.repeat(78);
const STYLE_PACKAGE_ROOT = fileURLToPath(new URL('../node_modules/', import.meta.url));

const packageDirOf = (moduleId: string): string | undefined => {
  const file = moduleId.replace(/^\0/, '').split('?')[0];
  const at = file.lastIndexOf(NODE_MODULES);
  if (at < 0) return undefined;
  const root = file.slice(0, at + NODE_MODULES.length);
  const [first, second] = file.slice(root.length).split('/');
  return root + (first.startsWith('@') ? `${first}/${second}` : first);
};

// Writes the licence and notice files of every package the bundle is built from next to it.
// `stylePackages` adds packages whose code reaches the bundle through PostCSS, where no module id names them.
const thirdPartyLicenses = (stylePackages: string[] = []): Plugin => ({
  name: 'third-party-licenses',
  apply: 'build',
  generateBundle() {
    const packageDirs = new Set(stylePackages.map((name) => `${STYLE_PACKAGE_ROOT}${name}`));
    Array.from(this.getModuleIds()).forEach((id) => {
      const dir = packageDirOf(id);
      if (dir) packageDirs.add(dir);
    });

    const sections = new Map<string, string>();
    packageDirs.forEach((dir) => {
      const { name, version, license } = JSON.parse(readFileSync(`${dir}/package.json`, 'utf8')) as {
        name: string;
        version: string;
        license?: string;
      };
      if (FIRST_PARTY.test(name)) return;

      const files = readdirSync(dir, { withFileTypes: true })
        .filter((entry) => entry.isFile() && LICENCE_FILE.test(entry.name))
        .map((entry) => entry.name)
        .sort();
      if (files.length === 0 && !license) this.error(`${name}@${version} names no licence`);

      const texts =
        files.length > 0
          ? files.map((file) => readFileSync(`${dir}/${file}`, 'utf8').trim())
          : ['The package ships no licence file; its package.json names the licence above.'];
      sections.set(
        `${name} ${version}`,
        [RULE, `${name} ${version} (${license ?? 'see below'})`, RULE, ...texts].join('\n'),
      );
    });

    const intro =
      'This bundle is built from the third-party packages below. Each section names a package\n' +
      'and reproduces the licence and notice files it ships, or names its licence where it ships none.';
    const body = Array.from(sections.keys())
      .sort()
      .map((key) => sections.get(key));
    this.emitFile({ type: 'asset', fileName: OUTPUT_FILE, source: `${[intro, ...body].join('\n\n')}\n` });
  },
});

export default thirdPartyLicenses;
