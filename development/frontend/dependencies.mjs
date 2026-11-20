import {createRequire} from 'node:module';
const require = createRequire(new URL('../../app/frontend/package.json', import.meta.url));
export const {JSDOM, VirtualConsole} = require('jsdom');
export const {createPowerSearchConfig} = await import(require.resolve('@astryxdesign/core/PowerSearch'));
