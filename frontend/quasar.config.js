// https://quasar.dev/quasar-cli-vite/quasar-config-file
import { defineConfig } from '#q-app';
import path from 'node:path';

export default defineConfig(() => ({
  // Fonts first: an @import of a remote stylesheet must open the bundled CSS.
  css: ['00-fonts/fonts.css', 'app.scss'],

  build: {
    vueRouterMode: 'history',
    sassVariables: 'src/css/quasar.variables.scss',
    extendViteConf(viteConf) {
      // Block Quasar's auto-injected CSS: app.scss imports it inside
      // @layer quasar-base so the GBDI overrides win without !important.
      // See src/css/README.md.
      const empty = path.resolve(__dirname, './src/css/empty.scss');
      viteConf.resolve ??= {};
      viteConf.resolve.alias ??= {};
      viteConf.resolve.alias['quasar/dist/quasar.sass'] = empty;
      viteConf.resolve.alias['quasar/dist/quasar.css'] = empty;
      viteConf.css ??= {};
      viteConf.css.preprocessorOptions ??= {};
      viteConf.css.preprocessorOptions.scss ??= {};
      viteConf.css.preprocessorOptions.scss.silenceDeprecations = ['import'];
    },
  },

  devServer: {
    open: false,
    // The backend serves everything under /api already: no rewrite.
    proxy: { '/api': `http://localhost:${process.env.BACKEND_PORT ?? 8000}` },
  },

  framework: {
    // Quasar's own component icons as inline SVG (no icon webfont).
    iconSet: 'svg-material-icons',
    cssAddon: false,
  },
}));
