// Local-only (untracked): lets Vite serve files resolved through the node_modules junction.
import { mergeConfig } from 'vite';
import base from './vite.config';

export default mergeConfig(base, {
  server: {
    fs: { allow: ['C:/Users/Owner/oxford-command-center'] },
    allowedHosts: ['<TAILNET_HOST>'],
  },
});
