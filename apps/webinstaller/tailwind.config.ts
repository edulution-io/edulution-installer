import type { Config } from 'tailwindcss';
import baseConfig from '@edulution-io/ui-kit/tailwind.config';

const config: Config = {
  presets: [baseConfig as Config],
  content: [
    './apps/webinstaller/src/**/*.{js,ts,jsx,tsx}',
    './libs/**/*.{js,ts,jsx,tsx}',
    './node_modules/@edulution-io/ui-kit/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        ciRed: '#dc2626',
        ciDarkGrey: '#2D2D30',
      },
    },
  },
  plugins: [],
};

export default config;
