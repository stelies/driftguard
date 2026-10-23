<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { scaleBand, scaleLinear, scaleTime } from 'd3';
	import Explain from './Explain.svelte';
	import { sectionText } from './narrative';
	import { F, META, ui, day, fmtTok, pct, showTip, hideTip, openSession, SERIES, BLOCKS } from './store.svelte';

	const hs = F.human;
	const total = hs.reduce((a, s) => a + s.tok, 0);
	const sum = (k: 'input' | 'output' | 'cache_read' | 'cache_write') => hs.reduce((a, s) => a + (s.tokens[k] ?? 0), 0);
	const parts = [['Cache reads', sum('cache_read')], ['Cache writes', sum('cache_write')], ['Input', sum('input')], ['Output', sum('output')]] as [string, number][];

	// per day / project / model
	const byDay = new Map<string, number>();
	for (const s of hs) byDay.set(day(s.start), (byDay.get(day(s.start)) ?? 0) + s.tok);
	const days = [...byDay.entries()].sort((a, b) => a[0].localeCompare(b[0]));
	const byProj = F.projects.slice().sort((a, b) => b.tokens - a.tokens).slice(0, 10);
	const byModel: Record<string, number> = {};
	for (const s of F.sessions) for (const [m, n] of Object.entries(s.models)) byModel[m] = (byModel[m] ?? 0) + n;
	const models = Object.entries(byModel).sort((a, b) => b[1] - a[1]).slice(0, 8);
	const modelTot = models.reduce((a, m) => a + m[1], 0);
	const top = hs.slice().sort((a, b) => b.tok - a.tok).slice(0, 10);

	// 5h blocks (all agents), p90 line
	let W = $state(900);
	const H = 220, pad = { l: 52, r: 12, t: 12, b: 24 };
	const dmax = Math.max(1, ...days.map((d) => d[1]));
	const dx = $derived(scaleBand(days.map((d) => d[0]), [pad.l, W - pad.r]).padding(0.15));
	const dy = scaleLinear([0, dmax], [H - pad.b, pad.t]);
	const P90 = META.summary.tokens.p90_block_tokens;
	const bl = BLOCKS;
	const bmax = Math.max(1, P90, ...bl.map((b) => b.tokens));
	const bx = $derived(scaleBand(bl.map((_, i) => String(i)), [pad.l, W - pad.r]).padding(0.1));
	const by = scaleLinear([0, bmax], [H - pad.b, pad.t]);
	const over = bl.filter((b) => b.tokens > P90).length;
</script>

<div class="space-y-6">
	<Explain text={sectionText('tokens')} />

	<div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
		{#each [['Total tokens', fmtTok(total), `${hs.length} sessions`], ['Cache-read share', pct(sum('cache_read'), total) + '%', 'cheap re-reads of context'], ['Top 10 sessions', pct(top.reduce((a, s) => a + s.tok, 0), total) + '%', 'share of all tokens'], ['Blocks over p90', `${over}/${bl.length}`, `p90 = ${fmtTok(P90)} per 5h block`]] as [k, v, sub]}
			<Card.Root class="gap-1 px-5 py-4"><div class="text-xs text-muted-foreground">{k}</div><div class="text-3xl font-semibold tabular-nums">{v}</div><div class="text-xs text-muted-foreground">{sub}</div></Card.Root>
		{/each}
	</div>

	<Card.Root class="gap-2 px-4">
		<div class="px-2 text-sm font-medium">Spend per day (by session start day)</div>
		<div bind:clientWidth={W}>
			<svg width={W} height={H}>
				{#each dy.ticks(4) as t}
					<line x1={pad.l} x2={W - pad.r} y1={dy(t)} y2={dy(t)} stroke="#2c2c2a" />
					<text x={pad.l - 8} y={dy(t) + 3} text-anchor="end" font-size="10" fill="#898781">{fmtTok(t)}</text>
				{/each}
				{#each days as [d, v], i}
					<rect x={dx(d)} y={dy(v)} width={dx.bandwidth()} height={H - pad.b - dy(v)} rx="2" fill="#3987e5" role="presentation"
						onmousemove={(e) => showTip(e, d, undefined, [['Tokens', fmtTok(v)]])} onmouseleave={hideTip} />
					{#if i % Math.ceil(days.length / 8) === 0}<text x={(dx(d) ?? 0) + dx.bandwidth() / 2} y={H - 6} text-anchor="middle" font-size="9" fill="#898781">{d.slice(5)}</text>{/if}
				{/each}
			</svg>
		</div>
	</Card.Root>

	<Card.Root class="gap-2 px-4">
		<div class="px-2 text-sm font-medium">5-hour blocks (all agents) with p90 line</div>
		<div>
			<svg width={W} height={H}>
				{#each by.ticks(4) as t}
					<line x1={pad.l} x2={W - pad.r} y1={by(t)} y2={by(t)} stroke="#2c2c2a" />
					<text x={pad.l - 8} y={by(t) + 3} text-anchor="end" font-size="10" fill="#898781">{fmtTok(t)}</text>
				{/each}
				{#each bl as b, i}
					<rect x={bx(String(i))} y={by(b.tokens)} width={bx.bandwidth()} height={H - pad.b - by(b.tokens)} fill={b.tokens > P90 ? '#d95926' : '#3987e5'} role="presentation"
						onmousemove={(e) => showTip(e, b.start.slice(0, 16).replace('T', ' '), undefined, [['Tokens', fmtTok(b.tokens)], ['Turns', String(b.turns)]])} onmouseleave={hideTip} />
				{/each}
				<line x1={pad.l} x2={W - pad.r} y1={by(P90)} y2={by(P90)} stroke="#f0efec" stroke-dasharray="4 4" />
				<text x={W - pad.r} y={by(P90) - 4} text-anchor="end" font-size="10" fill="#f0efec">p90 {fmtTok(P90)}</text>
			</svg>
		</div>
		{#if ui.agents.length}<p class="px-2 text-xs text-muted-foreground">Blocks cover all agents; the agent filter does not apply here.</p>{/if}
	</Card.Root>

	<div class="grid gap-6 lg:grid-cols-2">
		<Card.Root class="gap-2 px-6">
			<div class="text-sm font-medium">By project (top 10)</div>
			{#each byProj as p}
				<div class="flex items-center gap-3 text-sm">
					<span class="w-36 shrink-0 truncate text-muted-foreground">{p.name}</span>
					<span class="h-4 rounded-[4px] bg-[#3987e5]" style="width:{pct(p.tokens, byProj[0]?.tokens || 1) * 0.6}%"></span>
					<span class="text-xs tabular-nums">{fmtTok(p.tokens)}</span>
				</div>
			{/each}
		</Card.Root>
		<Card.Root class="gap-2 px-6">
			<div class="text-sm font-medium">By model (assistant turns) and token type</div>
			{#each models as [m, n], i}
				<div class="flex items-center gap-3 text-sm">
					<span class="w-44 shrink-0 truncate text-muted-foreground">{m}</span>
					<span class="h-4 rounded-[4px]" style="width:{pct(n, modelTot) * 0.5}%;background:{SERIES[i % 8]}"></span>
					<span class="text-xs tabular-nums">{pct(n, modelTot)}%</span>
				</div>
			{/each}
			<div class="mt-3 flex h-5 overflow-hidden rounded-md">
				{#each parts as [k, v], i}<div style="width:{pct(v, total)}%;background:{SERIES[i]}" title="{k} {fmtTok(v)}"></div>{/each}
			</div>
			<div class="flex flex-wrap gap-3 text-xs text-muted-foreground">{#each parts as [k, v], i}<span class="flex items-center gap-1.5"><span class="size-2.5 rounded-sm" style="background:{SERIES[i]}"></span>{k} {pct(v, total)}%</span>{/each}</div>
		</Card.Root>
	</div>

	<Card.Root class="gap-2 px-4">
		<div class="px-2 text-sm font-medium">Ten costliest sessions</div>
		{#each top as s}
			<button class="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent" onclick={() => openSession(s.id)}>
				<span class="w-20 shrink-0 text-xs text-muted-foreground tabular-nums">{day(s.start)}</span>
				<span class="w-32 shrink-0 truncate text-xs text-muted-foreground">{s.project}</span>
				<span class="truncate">{s.title ?? s.id}</span>
				<span class="ml-auto shrink-0 text-xs tabular-nums">{fmtTok(s.tok)} · {s.n} prompts</span>
			</button>
		{/each}
	</Card.Root>
</div>
