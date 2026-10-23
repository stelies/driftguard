<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { scaleBand, scaleLinear } from 'd3';
	import Explain from './Explain.svelte';
	import { headline } from './narrative';
	import {
		F, ACTIONS, HAS_FINDINGS, FINDINGS, SERIES, categoryOf, catColor, CATEGORY_ORDER, mean, showTip, hideTip, ui, monthOf, monthLabel, fmtTok, AGENT_LABEL
	} from './store.svelte';

	const human = F.human;
	const months = [...new Set(human.map((s) => monthOf(s.start)))].sort();
	const grpTop = Object.entries(human.reduce((a: Record<string, number>, s) => ((a[s.project] = (a[s.project] ?? 0) + s.n), a), {})).sort((a, b) => b[1] - a[1]).slice(0, 6).map((x) => x[0]);
	const grp = (s: (typeof human)[0]) => (HAS_FINDINGS ? categoryOf(s) : grpTop.includes(s.project) ? s.project : 'other');
	const M = months.map((m) => {
		const ss = human.filter((s) => monthOf(s.start) === m);
		const ps = ss.flatMap((s) => F.promptsBySession.get(s.id) ?? []);
		const byCat: Record<string, number> = {};
		for (const s of ss) byCat[grp(s)] = (byCat[grp(s)] ?? 0) + (F.promptsBySession.get(s.id)?.length ?? 0);
		return {
			m, sessions: ss.length, prompts: ps.length, q: mean(ss.map((s) => s.quality)), mot: mean(ss.map((s) => s.motivation)),
			dis: ps.length ? ps.filter((p) => p.kind.length).length / ps.length : 0, byCat, tok: ss.reduce((a, s) => a + s.tok, 0)
		};
	});
	const label = monthLabel;
	const last = M.at(-1);
	const kpis = [
		{ k: 'Transcripts', v: F.sessions.length, sub: `${F.sessions.length - human.length} auto-generated` },
		{ k: 'Real sessions', v: human.length, sub: last ? `${last.sessions} in ${label(last.m)} (${Math.round((100 * last.sessions) / (human.length || 1))}%)` : '' },
		{ k: 'Your prompts', v: F.prompts.length, sub: `${F.prompts.filter((p) => p.kind.length).length} were focus breaks` },
		{ k: 'Projects', v: F.projects.length, sub: HAS_FINDINGS ? `${F.projects.filter((p) => p.category === 'dopamine-build').length} dopamine · ${F.projects.filter((p) => p.category === 'abandoned').length} abandoned` : 'not judged yet' }
	];

	const W = 300, H = 150, pad = { l: 28, r: 8, t: 10, b: 22 };
	const x = scaleBand(months, [pad.l, W - pad.r]).padding(0.25);
	const smalls = [
		{ title: 'Real sessions / month', key: 'sessions', max: Math.max(1, ...M.map((d) => d.sessions)), fmt: (v: number) => String(Math.round(v)), bar: true },
		...(HAS_FINDINGS
			? [
					{ title: 'Prompt quality (1–5)', key: 'q', max: 5, fmt: (v: number) => v.toFixed(2), bar: false },
					{ title: 'Motivation (1–5)', key: 'mot', max: 5, fmt: (v: number) => v.toFixed(2), bar: false }
				]
			: [
					{ title: 'Prompts / month', key: 'prompts', max: Math.max(1, ...M.map((d) => d.prompts)), fmt: (v: number) => String(Math.round(v)), bar: true },
					{ title: 'Tokens / month', key: 'tok', max: Math.max(1, ...M.map((d) => d.tok)), fmt: fmtTok, bar: true }
				]),
		{ title: 'Focus-break rate', key: 'dis', max: Math.max(0.2, ...M.map((d) => d.dis)), fmt: (v: number) => Math.round(v * 100) + '%', bar: true }
	] as const;
	const cats = HAS_FINDINGS ? CATEGORY_ORDER.filter((c) => M.some((d) => d.byCat[c])) : [...grpTop, 'other'].filter((c) => M.some((d) => d.byCat[c]));
	const colorOf = (c: string) => (HAS_FINDINGS ? catColor(c) : c === 'other' ? '#5a5955' : SERIES[grpTop.indexOf(c) % SERIES.length]);
	const nameOf = (c: string) => (HAS_FINDINGS ? (ACTIONS[c]?.label ?? c) : c);
	const agentRows = Object.entries(human.reduce((a: Record<string, number>, s) => ((a[s.agent] = (a[s.agent] ?? 0) + 1), a), {}));
	let hoverCat = $state<string | null>(null);
</script>

<div class="space-y-6">
	<Card.Root class="gap-3 px-6">
		<div class="text-xs font-medium tracking-wide text-muted-foreground uppercase">Summary</div>
		<Explain text={headline()} />
	</Card.Root>

	<div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
		{#each kpis as k}
			<Card.Root class="gap-1 px-5 py-4">
				<div class="text-xs text-muted-foreground">{k.k}</div>
				<div class="text-3xl font-semibold tabular-nums">{k.v}</div>
				<div class="text-xs text-muted-foreground">{k.sub}</div>
			</Card.Root>
		{/each}
	</div>

	<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
		{#each smalls as c}
			{@const y = scaleLinear([0, c.max], [H - pad.b, pad.t])}
			<Card.Root class="gap-2 px-4 py-4">
				<div class="text-sm font-medium">{c.title}</div>
				<svg viewBox="0 0 {W} {H}" class="w-full">
					{#each y.ticks(3) as t}
						<line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="#2c2c2a" />
						<text x={pad.l - 6} y={y(t) + 3} text-anchor="end" font-size="9" fill="#898781">{c.fmt(t)}</text>
					{/each}
					{#if c.bar}
						{#each M as d}
							{@const v = (d as any)[c.key] ?? 0}
							<rect x={x(d.m)} y={y(v)} width={x.bandwidth()} height={H - pad.b - y(v)} rx="4" fill="#3987e5" />
						{/each}
					{:else}
						<path fill="none" stroke="#3987e5" stroke-width="2" d={'M' + M.filter((d) => (d as any)[c.key] != null).map((d) => `${x(d.m)! + x.bandwidth() / 2},${y((d as any)[c.key])}`).join('L')} />
						{#each M as d}{#if (d as any)[c.key] != null}<circle cx={x(d.m)! + x.bandwidth() / 2} cy={y((d as any)[c.key])} r="4" fill="#3987e5" stroke="#1a1a19" stroke-width="2" />{/if}{/each}
					{/if}
					{#each M as d}
						<text x={x(d.m)! + x.bandwidth() / 2} y={H - 6} text-anchor="middle" font-size="9" fill="#898781">{label(d.m)}</text>
						<rect role="presentation" x={x(d.m)! - 4} y={pad.t} width={x.bandwidth() + 8} height={H - pad.t - pad.b} fill="transparent"
							onmousemove={(e) => showTip(e, label(d.m), undefined, [[c.title, (d as any)[c.key] == null ? '–' : c.fmt((d as any)[c.key])], ['Sessions', String(d.sessions)], ['Prompts', String(d.prompts)]])}
							onmouseleave={hideTip} />
					{/each}
				</svg>
			</Card.Root>
		{/each}
	</div>

	<Card.Root class="gap-3 px-6">
		<div class="text-sm font-medium">{HAS_FINDINGS ? 'Where your prompts went, by project verdict' : 'Where your prompts went, by project'}</div>
		<div class="flex flex-wrap gap-3 text-xs">
			{#each cats as c}
				<button class="flex items-center gap-1.5 rounded px-1 {hoverCat && hoverCat !== c ? 'opacity-40' : ''}" onmouseenter={() => (hoverCat = c)} onmouseleave={() => (hoverCat = null)} onclick={() => (ui.section = 'projects')}>
					<span class="size-2.5 rounded-sm" style="background:{colorOf(c)}"></span>{nameOf(c)}
				</button>
			{/each}
		</div>
		<div class="space-y-2">
			{#each M as d}
				{@const tot = Object.values(d.byCat).reduce((a, b) => a + b, 0) || 1}
				<div class="flex items-center gap-3">
					<span class="w-12 text-xs text-muted-foreground">{label(d.m)}</span>
					<div class="flex h-6 flex-1 gap-[2px]">
						{#each cats as c}
							{#if d.byCat[c]}
								<div role="presentation" class="h-full rounded-[4px] transition-opacity {hoverCat && hoverCat !== c ? 'opacity-25' : ''}"
									style="width:{(100 * d.byCat[c]) / tot}%;background:{colorOf(c)}"
									onmousemove={(e) => showTip(e, `${label(d.m)} · ${nameOf(c)}`, undefined, [['Prompts', String(d.byCat[c])], ['Share', Math.round((100 * d.byCat[c]) / tot) + '%']])}
									onmouseleave={hideTip}></div>
							{/if}
						{/each}
					</div>
					<span class="w-16 text-right text-xs text-muted-foreground tabular-nums">{d.prompts}</span>
				</div>
			{/each}
		</div>
	</Card.Root>

	{#if agentRows.length > 1}
		<Card.Root class="gap-2 px-6">
			<div class="text-sm font-medium">Sessions by agent</div>
			<div class="flex flex-wrap gap-4 text-sm">
				{#each agentRows as [a, n]}<span><span class="text-muted-foreground">{AGENT_LABEL[a] ?? a}</span> <span class="tabular-nums">{n}</span></span>{/each}
			</div>
		</Card.Root>
	{/if}

	{#if FINDINGS.patterns.length}
		<Card.Root class="gap-3 px-6">
			<div class="text-sm font-medium">Patterns the agent found</div>
			<ul class="grid gap-2 text-sm text-muted-foreground md:grid-cols-2">
				{#each FINDINGS.patterns as p}<li class="rounded-lg bg-muted/40 p-3">{p}</li>{/each}
			</ul>
		</Card.Root>
	{/if}
</div>
