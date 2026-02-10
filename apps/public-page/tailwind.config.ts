import type { Config } from 'tailwindcss';
import baseConfig from '@edulution-io/ui-kit/tailwind.config';

const config: Config = {
  presets: [baseConfig as Config],
  content: [
    './apps/public-page/src/**/*.{js,ts,jsx,tsx}',
    './libs/**/*.{js,ts,jsx,tsx}',
    './node_modules/@edulution-io/ui-kit/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        ciLightGreen: 'var(--ci-light-green)',
        ciDarkBlue: 'var(--ci-dark-blue)',
        ciRed: '#dc2626',
        ciDarkGrey: '#2D2D30',
        ciGrey: '#848493',
      },
      backgroundImage: {
        ciGreenToBlue: 'linear-gradient(45deg, var(--ci-light-green), var(--ci-dark-blue))',
      },
    },
  },
  plugins: [],
};

export default config;
