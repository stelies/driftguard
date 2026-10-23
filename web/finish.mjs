// Post-build: emit ../driftguard/report/template.html, one self-contained file (CSS + JS inline) that still contains
// the `__DG_DATA__` placeholder; driftguard/report.py fills it in.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
const dist = new URL('./dist/', import.meta.url);
let html = readFileSync(new URL('index.html', dist), 'utf8').replaceAll('"/_app/', '"./_app/');
writeFileSync(new URL('index.html', dist), html);

const jsPath = html.match(/import\("\.\/(_app\/immutable\/[^"]+\.js)"\)/)[1];
// Inline module: the bundle ends with `export{… as start}`; hand start() to the bootstrap element instead.
const js = readFileSync(new URL(jsPath, dist), 'utf8')
	.replaceAll('</script', '<\\/script').replaceAll('<script', '<\\script').replaceAll('<!--', '<\\!--')
	.replace(/export\{([^}]*)\};?\s*$/, (_, list) => {
		const start = list.split(',').map((x) => x.trim().split(/\s+as\s+/)).find(([, n]) => n === 'start')[0];
		return `${start}(window.__lxEl);`;
	});
let one = html.replace(/<link[^>]+href="\.\/(_app\/[^"]+\.css)"[^>]*>/g, (_, p) => `<style>${readFileSync(new URL(p, dist), 'utf8')}</style>`);
one = one.replace(/<link[^>]*rel="modulepreload"[^>]*>/g, "").replace(/<link[^>]*rel="icon"[^>]*>/g, "");
one = one.replace(/import\("\.\/_app\/[^"]+"\)\.then\(\(app\) => \{\s*app\.start\(element\)\s*\}\);/, () => 'window.__lxEl = element;');
one = one.replace('</body>', () => `<script type="module">${js}</script>\n</body>`);
if (!one.includes('__DG_DATA__')) throw new Error('placeholder __DG_DATA__ missing from build');
const out = new URL('../driftguard/report/', import.meta.url);
mkdirSync(out, { recursive: true });
writeFileSync(new URL('template.html', out), one);
console.log('driftguard/report/template.html', (one.length / 1024) | 0, 'KB');
