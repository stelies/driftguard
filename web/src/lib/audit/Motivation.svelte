<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { scaleTime, scaleLinear, brushX, select, line, curveMonotoneX } from 'd3';
	import Explain from './Explain.svelte';
	import Empty from './Empty.svelte';
	import { sectionText } from './narrative';
	import { F, HAS_FINDINGS, FINDINGS, T0, T1, tickFmt, day, mean, ui, showTip, hideTip, openSession, catColor, categoryOf } from './store.svelte';

	const days = [...new Set(F.human.map((s) => day(s.start)))].sort();
	const pts = days.map((d) => {
		const ss = F.human.filter((s) => day(s.start) === d);
		const ps = ss.flatMap((s) => F.promptsBySession.get(s.id) ?? []);
		return { d, date: new Date(d), mot: mean(ss.map((s) => s.motivation)), q: mean(ss.map((s) => s.quality)), n: ss.length, rage: ps.filter((p) => p.kind.includes('rage')).length, ss };
	});
	// Event lines: drift dates from the findings, else the three worst frustration days.
	const EVENTS: [string, string][] = HAS_FINDINGS && F.projects.some((p) => p.drift?.length)
		? F.projects.flatMap((p) => (p.drift ?? []).map((d) => [d.date.slice(0, 10), `${p.name}: ${d.to}`.slice(0, 28)] as [string, string])).slice(0, 10)
		: pts.slice().sort((a, b) => b.rage - a.rage).filter((p) => p.rage > 0).slice(0, 3).map((p) => [p.d, `${p.rage} frustration`] as [string, string]);
	let W = $state(900);
	const H = 220, pad = { l: 34, r: 14, t: 18, b: 24 };
	let range = $state<[Date, Date] | null>(null);
	let metric = $state<'mot' | 'q'>(HAS_FINDINGS ? 'mot' : 'q');
	const x = $derived(scaleTime([T0, T1], [pad.l, W - pad.r]));
	const maxN = Math.max(1, ...pts.map((p) => p.n));
	const yFor = (k: string) => (k === 'n' ? scaleLinear([0, maxN], [H - pad.b, pad.t]) : scaleLinear([1, 5], [H - pad.b, pad.t]));
	const CHARTS: [string, string][] = HAS_FINDINGS ? [['mot', 'Motivation (1–5)'], ['q', 'Prompt quality (1–5)']] : [['n', 'Real sessions per day']];
	const ticksFor = (k: string) => (k === 'n' ? yFor(k).ticks(4) : [1, 2, 3, 4, 5]);
	const path = (k: 'mot' | 'q' | 'n') => line<(typeof pts)[0]>().defined((p) => p[k] != null).x((p) => x(p.date)).y((p) => yFor(k)(p[k]!)).curve(curveMonotoneX)(pts) ?? '';
	let hover = $state<(typeof pts)[0] | null>(null);
	function onMove(e: MouseEvent) {
		const r = (e.currentTarget as SVGElement).getBoundingClientRect();
		const mx = ((e.clientX - r.left) / r.width) * W;
		let best = pts[0];
		for (const p of pts) if (Math.abs(x(p.date) - mx) < Math.abs(x(best.date) - mx)) best = p;
		hover = best;
		showTip(e, best.d, undefined, [...(HAS_FINDINGS ? [['Motivation', best.mot?.toFixed(1) ?? '–'], ['Quality', best.q?.toFixed(1) ?? '–']] as [string, string][] : []), ['Sessions', String(best.n)], ['Frustration prompts', String(best.rage)]]);
	}
	function brush(node: SVGGElement) {
		const b = brushX().extent([[pad.l, pad.t], [W - pad.r, H - pad.b]]).on('end', (ev) => {
			range = ev.selection ? [x.invert(ev.selection[0]), x.invert(ev.selection[1])] : null;
		});
		select(node).call(b);
		return { destroy: () => select(node).on('.brush', null) };
	}
	const listed = $derived(
		(range ? F.human.filter((s) => new Date(s.start) >= range![0] && new Date(s.start) <= range![1]) : F.human)
			.slice().sort((a, b) => !HAS_FINDINGS ? b.n - a.n : (metric === 'mot' ? (a.motivation ?? 9) - (b.motivation ?? 9) : (a.quality ?? 9) - (b.quality ?? 9)))
	);
</script>

<div class="space-y-6">
	<Explain text={sectionText('motivation')} />
	{#if !HAS_FINDINGS}<Empty title="Motivation and quality scores need the agent pass" />{/if}
	<Card.Root class="gap-2 px-4">
		<div class="flex flex-wrap items-center gap-2 px-2">
			<span class="text-sm font-medium">Daily average, real sessions only</span>
			<span class="text-xs text-muted-foreground">Hover for the day · click a dot to open it · drag across the chart to filter the list below</span>
			{#if range}<Button size="sm" variant="secondary" class="ml-auto" onclick={() => (range = null)}>Clear range</Button>{/if}
		</div>
		<div bind:clientWidth={W} class="w-full">
			{#each CHARTS as [k, title]}
				<div class="px-2 pt-2 text-xs text-muted-foreground">{title}</div>
				<svg width={W} height={H} role="presentation" onmousemove={onMove} onmouseleave={() => { hover = null; hideTip(); }}>
					{#each ticksFor(k) as t}
						<line x1={pad.l} x2={W - pad.r} y1={yFor(k)(t)} y2={yFor(k)(t)} stroke="#2c2c2a" />
						<text x={pad.l - 8} y={yFor(k)(t) + 3} text-anchor="end" font-size="10" fill="#898781">{t}</text>
					{/each}
					{#each x.ticks(6) as t}<text x={x(t)} y={H - 6} text-anchor="middle" font-size="10" fill="#898781">{tickFmt(t)}</text>{/each}
					{#if k === CHARTS[0][0]}
						{#each EVENTS as [d, l], i}
							<line x1={x(new Date(d))} x2={x(new Date(d))} y1={pad.t} y2={H - pad.b} stroke="#383835" stroke-dasharray="2 3" />
							<text x={x(new Date(d)) + 3} y={pad.t - 4 + (i % 2) * 10} font-size="9" fill="#898781">{l}</text>
						{/each}
					{/if}
					{#key W}<g use:brush></g>{/key}
					<path d={path(k as 'mot' | 'q' | 'n')} fill="none" stroke="#3987e5" stroke-width="2" pointer-events="none" />
					{#each pts as p}
						{#if p[k as 'mot' | 'q' | 'n'] != null}
							<circle cx={x(p.date)} cy={yFor(k)(p[k as 'mot' | 'q' | 'n']!)} r={3 + Math.min(5, p.n)} fill={p.rage ? '#d95926' : '#3987e5'} stroke="#1a1a19" stroke-width="2"
								class="cursor-pointer" role="button" tabindex="-1" onclick={() => (ui.day = p.d)} onkeydown={() => {}} />
						{/if}
					{/each}
					{#if hover}<line x1={x(hover.date)} x2={x(hover.date)} y1={pad.t} y2={H - pad.b} stroke="#c3c2b7" pointer-events="none" />{/if}
				</svg>
			{/each}
		</div>
		<div class="flex gap-4 px-2 text-xs text-muted-foreground">
			<span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-[#3987e5]"></span>calm day</span>
			<span class="flex items-center gap-1.5"><span class="size-2.5 rounded-full bg-[#d95926]"></span>day with frustration prompts</span>
			<span>dot size = sessions that day</span>
		</div>
	</Card.Root>

	<Card.Root class="gap-2 px-4">
		<div class="flex flex-wrap items-center gap-2 px-2">
			<span class="text-sm font-medium">{range ? `Sessions ${range[0].toISOString().slice(0, 10)} → ${range[1].toISOString().slice(0, 10)}` : 'All sessions'}{HAS_FINDINGS ? ', lowest first' : ', most prompts first'}</span>
			<div class="ml-auto flex gap-1">
				{#if HAS_FINDINGS}
					<Button size="sm" variant={metric === 'mot' ? 'secondary' : 'ghost'} onclick={() => (metric = 'mot')}>by motivation</Button>
					<Button size="sm" variant={metric === 'q' ? 'secondary' : 'ghost'} onclick={() => (metric = 'q')}>by quality</Button>
				{/if}
			</div>
		</div>
		<div class="max-h-96 overflow-y-auto">
			{#each listed as s}
				<button class="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent" onclick={() => openSession(s.id)}>
					<span class="w-20 shrink-0 text-xs text-muted-foreground tabular-nums">{day(s.start)}</span>
					<span class="size-2.5 shrink-0 rounded-sm" style="background:{catColor(categoryOf(s))}"></span>
					<span class="w-32 shrink-0 truncate text-xs text-muted-foreground">{s.project}</span>
					<span class="truncate">{s.evidence ? `“${s.evidence}”` : (s.title ?? s.id)}</span>
					<span class="ml-auto shrink-0 text-xs tabular-nums">{HAS_FINDINGS ? `M${s.motivation ?? '–'} · Q${s.quality ?? '–'}` : `${s.n} prompts`}</span>
				</button>
			{/each}
		</div>
	</Card.Root>
</div>
