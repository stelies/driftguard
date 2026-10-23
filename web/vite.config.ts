import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	build: { assetsInlineLimit: 32000, chunkSizeWarningLimit: 3072, minify: true },
	plugins: [tailwindcss(), sveltekit()]
});
