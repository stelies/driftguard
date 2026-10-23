import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({ assets: 'dist', fallback: 'index.html', pages: 'dist', precompress: false, strict: true }),
		output: { bundleStrategy: 'single' },
		paths: { relative: true },
		// Hash router: the report is a single file opened from disk or any prefix.
		router: { type: 'hash' }
	},
	preprocess: [vitePreprocess()]
};
export default config;
