<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Switch } from '$lib/components/ui/switch';
	import { interpolateRgb, color as d3color } from 'd3';
	import { untrack } from 'svelte';
	import Explain from './Explain.svelte';
	import { sectionText } from './narrative';
	import { F, ACTIONS, T0, T1, monthOf, monthLabel, catColor, categoryOf, CATEGORY_ORDER, local, day, openSession, openProject, showTip, hideTip } from './store.svelte';

	type V3 = [number, number, number];
	type Pt = { p: V3; r: number; c: string; title: string; rows: [string, string][]; click: () => void };
	type Box = { x0: number; z0: number; x1: number; z1: number; h: number; c: string; title: string; rows: [string, string][]; click?: () => void };
	type Scene = { pts: Pt[]; boxes: Box[]; axes: [string, string, string]; ticks: { p: V3; t: string }[] };

	let mode = $state<'cloud' | 'terrain' | 'towers'>('cloud');
	let yaw = $state(-0.6), pitch = $state(0.45), zoom = $state(1), auto = $state(true);
	let canvas: HTMLCanvasElement;
	let Wc = $state(900);
	const Hc = 560;

	const t0 = T0.getTime(), t1 = T1.getTime();
	const nx = (t: string) => ((new Date(t).getTime() - t0) / (t1 - t0)) * 2 - 1;
	const h = (s: string) => ((s.charCodeAt(2) * 13 + s.charCodeAt(7) * 7) % 100) / 100 - 0.5;

	function cloud(): Scene {
		const pts: Pt[] = F.human.filter((s) => s.motivation != null && s.quality != null).map((s) => ({
			p: [nx(s.start), ((s.motivation! - 1) / 4) * 2 - 1 + h(s.id) * 0.12, ((s.quality! - 1) / 4) * 2 - 1 + h(s.id.slice(3)) * 0.12],
			r: 3 + Math.sqrt(F.promptsBySession.get(s.id)?.length ?? 1) * 1.6,
			c: catColor(categoryOf(s)),
			title: `${day(s.start)} · ${s.project}`,
			rows: [['Motivation', String(s.motivation)], ['Quality', String(s.quality)], ['Prompts', String(s.n)], ['Verdict', ACTIONS[categoryOf(s)]?.label ?? '']],
			click: () => openSession(s.id)
		}));
		const ms = [...new Set(F.human.map((s) => monthOf(s.start)))].sort().slice(-8);
		const ticks = [
			...ms.map((m) => ({ p: [Math.max(-1, nx(m + '-01T00:00:00Z')), -1.12, -1.1] as V3, t: monthLabel(m) })),
			{ p: [-1.15, 1, -1.1] as V3, t: 'mot 5' }, { p: [-1.15, -1, -1.1] as V3, t: 'mot 1' },
			{ p: [1.12, -1.12, 1] as V3, t: 'quality 5' }, { p: [1.12, -1.12, -1] as V3, t: 'quality 1' }
		];
		return { pts, boxes: [], axes: ['date →', 'motivation ↑', 'prompt quality ↗'], ticks };
	}
	function terrain(): Scene {
		const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
		const n = Array.from({ length: 7 * 24 }, () => ({ n: 0, d: 0 }));
		for (const p of F.prompts) { const t = local(p.t), c = n[((t.getUTCDay() + 6) % 7) * 24 + t.getUTCHours()]; c.n++; if (p.kind.length) c.d++; }
		const max = Math.max(1, ...n.map((c) => c.n));
		const ramp = interpolateRgb('#cde2fb', '#d95926');
		const boxes: Box[] = [];
		n.forEach((c, i) => {
			const w = Math.floor(i / 24), hr = i % 24, x0 = (hr / 24) * 2 - 1, z0 = (w / 7) * 2 - 1;
			boxes.push({ x0: x0 + 0.01, x1: x0 + 2 / 24 - 0.01, z0: z0 + 0.02, z1: z0 + 2 / 7 - 0.02, h: c.n ? 0.03 + (c.n / max) * 1.9 : 0.01,
				c: c.n ? ramp(c.n >= 3 ? c.d / c.n : 0) : '#2c2c2a', title: `${WD[w]} ${String(hr).padStart(2, '0')}:00`,
				rows: [['Prompts', String(c.n)], ['Disconnect rate', c.n ? Math.round((100 * c.d) / c.n) + '%' : '–']] });
		});
		const ticks = [0, 6, 12, 18].map((hr) => ({ p: [(hr / 24) * 2 - 1, -1.05, -1.15] as V3, t: hr + ':00' })).concat(WD.map((wd, w) => ({ p: [-1.15, -1.05, (w / 7) * 2 - 1 + 1 / 7] as V3, t: wd })));
		return { pts: [], boxes, axes: ['hour of day →', 'prompts ↑ (red = disconnects)', 'weekday ↗'], ticks };
	}
	function towers(): Scene {
		const months = [...new Set(F.human.map((s) => monthOf(s.start)))].sort().slice(-8);
		const projs = F.projects
			.map((p) => ({ p, ss: F.human.filter((s) => s.project === p.name) })).filter((x) => x.ss.length)
			.sort((a, b) => CATEGORY_ORDER.indexOf(a.p.category) - CATEGORY_ORDER.indexOf(b.p.category));
		const max = Math.max(1, ...projs.flatMap((x) => months.map((m) => x.ss.filter((s) => monthOf(s.start) === m).length)));
		const boxes: Box[] = [];
		projs.forEach((x, j) => months.forEach((m, i) => {
			const k = x.ss.filter((s) => monthOf(s.start) === m).length;
			if (!k) return;
			const x0 = (i / months.length) * 2 - 1, z0 = (j / projs.length) * 2 - 1;
			boxes.push({ x0: x0 + 0.05, x1: x0 + 2 / months.length - 0.05, z0: z0 + 0.012, z1: z0 + 2 / projs.length - 0.012, h: 0.04 + (k / max) * 1.9, c: catColor(x.p.category),
				title: `${x.p.name} · ${monthLabel(m)}`, rows: [['Sessions', String(k)], ['Verdict', ACTIONS[x.p.category]?.label ?? '']], click: () => openProject(x.p.name) });
		}));
		const ticks = months.map((m, i) => ({ p: [(i / months.length) * 2 - 1 + 1 / months.length, -1.05, -1.15] as V3, t: monthLabel(m) }))
			.concat(projs.map((x, j) => ({ p: [1.08, -1.05, (j / projs.length) * 2 - 1 + 1 / projs.length] as V3, t: x.p.name.slice(0, 18) })));
		return { pts: [], boxes, axes: ['month →', 'sessions ↑', 'project ↗'], ticks };
	}
	const scene = $derived(mode === 'cloud' ? cloud() : mode === 'terrain' ? terrain() : towers());

	function proj([x, y, z]: V3): [number, number, number] {
		const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
		const x1 = x * cy - z * sy, z1 = x * sy + z * cy;
		const y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
		const f = (Math.min(Wc, Hc) * 0.36 * zoom * 3.6) / (z2 + 3.6);
		return [Wc / 2 + x1 * f, Hc / 2 - y2 * f, z2];
	}
	const shade = (c: string, k: number) => { const o = d3color(c)!.rgb(); return `rgb(${o.r * k},${o.g * k},${o.b * k})`; };
	let hits: { x: number; y: number; r: number; item: Pt | Box; z: number }[] = [];
	let hovered: Pt | Box | null = null;
	let hoverKey = 0; // bumps when the hovered item changes so the loop knows to redraw

	function draw() {
		const ctx = canvas?.getContext('2d');
		if (!ctx) return;
		const dpr = devicePixelRatio || 1;
		// Resizing a canvas reallocates it: only do it when the size actually changed.
		if (canvas.width !== Math.round(Wc * dpr) || canvas.height !== Math.round(Hc * dpr)) {
			canvas.width = Math.round(Wc * dpr);
			canvas.height = Math.round(Hc * dpr);
		}
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, Wc, Hc);
		ctx.lineWidth = 1; ctx.strokeStyle = '#383835';
		const C: V3[] = [[-1, -1, -1], [1, -1, -1], [1, -1, 1], [-1, -1, 1], [-1, 1, -1], [1, 1, -1], [1, 1, 1], [-1, 1, 1]];
		for (const [a, b] of [[0, 1], [1, 2], [2, 3], [3, 0], [0, 4], [1, 5], [2, 6], [3, 7], [4, 5], [5, 6], [6, 7], [7, 4]]) {
			const p = proj(C[a]), q = proj(C[b]); ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
		}
		ctx.strokeStyle = '#2c2c2a';
		for (let i = -0.5; i <= 0.5; i += 0.5) for (const L of [[[-1, -1, i], [1, -1, i]], [[i, -1, -1], [i, -1, 1]]] as V3[][]) {
			const p = proj(L[0]), q = proj(L[1]); ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
		}
		hits = [];
		const faces: { z: number; pts: [number, number][]; fill: string }[] = [];
		for (const b of scene.boxes) {
			const y0 = -1, y1 = -1 + b.h;
			const v = (x: number, y: number, z: number) => proj([x, y, z]);
			const P = [v(b.x0, y0, b.z0), v(b.x1, y0, b.z0), v(b.x1, y0, b.z1), v(b.x0, y0, b.z1), v(b.x0, y1, b.z0), v(b.x1, y1, b.z0), v(b.x1, y1, b.z1), v(b.x0, y1, b.z1)];
			const isH = hovered === b;
			const F: [number[], number][] = [[[4, 5, 6, 7], 1], [[0, 1, 5, 4], 0.62], [[1, 2, 6, 5], 0.78], [[2, 3, 7, 6], 0.62], [[3, 0, 4, 7], 0.78]];
			for (const [ix, k] of F) faces.push({ z: ix.reduce((a, i) => a + P[i][2], 0) / 4, pts: ix.map((i) => [P[i][0], P[i][1]]), fill: isH ? shade('#f0efec', k) : shade(b.c, k) });
			const top = [4, 5, 6, 7].map((i) => P[i]);
			hits.push({ x: top.reduce((a, p) => a + p[0], 0) / 4, y: top.reduce((a, p) => a + p[1], 0) / 4, r: 10, item: b, z: Math.min(...top.map((p) => p[2])) });
		}
		faces.sort((a, b) => b.z - a.z);
		for (const f of faces) {
			ctx.beginPath(); f.pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
			ctx.fillStyle = f.fill; ctx.fill(); ctx.strokeStyle = '#1a1a19'; ctx.lineWidth = 0.6; ctx.stroke();
		}
		const pts = scene.pts.map((p) => ({ p, s: proj(p.p) })).sort((a, b) => b.s[2] - a.s[2]);
		for (const { p, s } of pts) {
			const r = p.r * (3.6 / (s[2] + 3.6)) * zoom;
			ctx.beginPath(); ctx.arc(s[0], s[1], r, 0, Math.PI * 2);
			ctx.fillStyle = hovered === p ? '#f0efec' : p.c; ctx.globalAlpha = 0.9; ctx.fill(); ctx.globalAlpha = 1;
			ctx.strokeStyle = '#1a1a19'; ctx.lineWidth = 2; ctx.stroke();
			hits.push({ x: s[0], y: s[1], r: Math.max(8, r + 3), item: p, z: s[2] });
		}
		ctx.fillStyle = '#898781'; ctx.font = '11px system-ui';
		for (const t of scene.ticks) { const s = proj(t.p); ctx.fillText(t.t, s[0] - 12, s[1] + 4); }
		ctx.fillStyle = '#c3c2b7'; ctx.font = '12px system-ui';
		const ax = [proj([0, -1.3, -1.25]), proj([-1.3, 0.2, -1.2]), proj([1.3, -1.25, 0])];
		scene.axes.forEach((a, i) => ctx.fillText(a, ax[i][0] - 30, ax[i][1]));
	}

	$effect(() => {
		void scene; void Wc;
		let raf = 0;
		// Redraw only when something changed (rotation, zoom, hover, resize); auto-rotate is capped at ~30 fps
		// and pauses while the tab is hidden, so the report never starves the browser of paint time.
		let last = 0, key = '';
		const loop = (now = 0) => {
			raf = requestAnimationFrame(loop);
			if (document.hidden || now - last < 33) return;
			last = now;
			if (auto && !dragging) yaw += 0.007;
			const k = `${yaw.toFixed(4)}|${pitch.toFixed(4)}|${zoom}|${Wc}|${hoverKey}`;
			if (k === key) return;
			key = k;
			draw();
		};
		untrack(loop);
		return () => cancelAnimationFrame(raf);
	});

	let dragging = false, lx = 0, ly = 0, moved = 0;
	function pick(e: PointerEvent | MouseEvent) {
		const r = canvas.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
		let best: (typeof hits)[0] | null = null;
		for (const hh of hits) { const d = Math.hypot(hh.x - mx, hh.y - my); if (d < hh.r && (!best || hh.z < best.z)) best = hh; }
		return best?.item ?? null;
	}
	const down = (e: PointerEvent) => { dragging = true; moved = 0; lx = e.clientX; ly = e.clientY; canvas.setPointerCapture(e.pointerId); };
	const move = (e: PointerEvent) => {
		if (dragging) {
			yaw += (e.clientX - lx) * 0.008; pitch = Math.max(-1.4, Math.min(1.4, pitch + (e.clientY - ly) * 0.006));
			moved += Math.abs(e.clientX - lx) + Math.abs(e.clientY - ly); lx = e.clientX; ly = e.clientY; hideTip(); return;
		}
		const it = pick(e); if (it !== hovered) hoverKey++; hovered = it;
		if (it) showTip(e, it.title, undefined, it.rows); else hideTip();
		canvas.style.cursor = it ? 'pointer' : 'grab';
	};
	const up = (e: PointerEvent) => { dragging = false; if (moved < 5) { const it = pick(e); it && 'click' in it && it.click?.(); } };
	const wheel = (e: WheelEvent) => { e.preventDefault(); zoom = Math.max(0.5, Math.min(3, zoom * (e.deltaY > 0 ? 0.92 : 1.08))); };
	const VIEWS = [['cloud', 'Sessions cloud'], ['terrain', 'Brain terrain'], ['towers', 'Project towers']] as const;
	const legendCats = CATEGORY_ORDER.filter((c) => F.projects.some((p) => p.category === c));
</script>

<div class="space-y-6">
	<Explain text={sectionText('three')} />
	<Card.Root class="gap-3 px-4">
		<div class="flex flex-wrap items-center gap-2 px-2">
			{#each VIEWS as [id, l]}<Button size="sm" variant={mode === id ? 'secondary' : 'ghost'} onclick={() => (mode = id)}>{l}</Button>{/each}
			<label class="ml-auto flex items-center gap-2 text-xs">Auto-rotate <Switch bind:checked={auto} /></label>
			<Button size="sm" variant="ghost" onclick={() => { yaw = -0.6; pitch = 0.45; zoom = 1; }}>Reset view</Button>
		</div>
		<div bind:clientWidth={Wc} class="overflow-hidden rounded-xl bg-[#1a1a19]">
			<canvas bind:this={canvas} style="width:{Wc}px;height:{Hc}px;touch-action:none" onpointerdown={down} onpointermove={move} onpointerup={up}
				onpointerleave={() => { if (hovered) hoverKey++; hovered = null; hideTip(); }} onwheel={wheel}></canvas>
		</div>
		<div class="flex flex-wrap gap-3 px-2 text-xs text-muted-foreground">
			{#if mode === 'terrain'}
				<span class="flex items-center gap-1.5"><span class="h-2.5 w-16 rounded-sm" style="background:linear-gradient(90deg,#cde2fb,#d95926)"></span>0% → 100% disconnects</span>
				<span>height = prompts in that hour</span>
			{:else}
				{#each legendCats as c}<span class="flex items-center gap-1.5"><span class="size-2.5 rounded-sm" style="background:{catColor(c)}"></span>{ACTIONS[c]?.label}</span>{/each}
				<span>· drag = rotate · wheel = zoom · click = open</span>
			{/if}
		</div>
	</Card.Root>
</div>
