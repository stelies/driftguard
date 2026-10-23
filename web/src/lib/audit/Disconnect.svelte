<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { scaleBand, scaleLinear, scaleSqrt, interpolateRgb } from 'd3';
	import Explain from './Explain.svelte';
	import { sectionText, stats } from './narrative';
	const cl = stats().cliff;
	import { F, sessionById, kindColor, KIND_LABEL, KINDS, local, day, showTip, hideTip, openSession, short, TZ_LABEL } from './store.svelte';

	// 1. focus decay by prompt index
	const MAXI = 15;
	const idx = Array.from({ length: MAXI + 1 }, (_, i) => i);
	const decay = idx.map((i) => {
		const ps = F.prompts.filter((p) => (i === MAXI ? p.i >= MAXI : p.i === i));
		const r: Record<string, number> = { n: ps.length, any: ps.filter((p) => p.kind.length).length / (ps.length || 1) };
		for (const k of KINDS) r[k] = ps.filter((p) => p.kind[0] === k).length / (ps.length || 1);
		return r;
	});
	let W = $state(900);
	const H = 240, pad = { l: 40, r: 10, t: 14, b: 30 };
	const x = $derived(scaleBand(idx.map(String), [pad.l, W - pad.r]).padding(0.2));
	const y = scaleLinear([0, 0.7], [H - pad.b, pad.t]);

	// 2. heatmap hour x weekday (local)
	const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
	const cells = WD.flatMap((_, w) => Array.from({ length: 24 }, (_, h) => ({ w, h, n: 0, dis: 0, ps: [] as typeof F.prompts })));
	for (const p of F.prompts) {
		const d = local(p.t), w = (d.getUTCDay() + 6) % 7, h = d.getUTCHours(), c = cells[w * 24 + h];
		c.n++; c.ps.push(p); if (p.kind.length) c.dis++;
	}
	const maxN = Math.max(1, ...cells.map((c) => c.n));
	const ramp = interpolateRgb('#184f95', '#cde2fb');
	let cell = $state<(typeof cells)[0] | null>(null);
	const byHour = Array.from({ length: 24 }, (_, h) => {
		const cs = cells.filter((c) => c.h === h);
		const n = cs.reduce((a, c) => a + c.n, 0);
		return { h, n, rate: n ? cs.reduce((a, c) => a + c.dis, 0) / n : 0 };
	});
	const worstHour = byHour.filter((b) => b.n >= 20).sort((a, b) => b.rate - a.rate)[0] ?? byHour.filter((b) => b.n).sort((a, b) => b.rate - a.rate)[0] ?? { h: 0, rate: 0 };

	// 3. stats
	const withDis = F.human.filter((s) => (F.promptsBySession.get(s.id) ?? []).some((p) => p.kind.length));
	let afterAway = 0, afterAwaySwitch = 0;
	for (const ps of F.promptsBySession.values()) ps.forEach((p, i) => { if (i && ps[i].kind.includes('away')) { afterAway++; if (p.kind.includes('switch')) afterAwaySwitch++; } });
	const firsts = withDis.map((s) => (F.promptsBySession.get(s.id) ?? []).find((p) => p.kind.length)!.i + 1).sort((a, b) => a - b);
	const tiles = [
		['Sessions with a disconnect', `${withDis.length}/${F.human.length}`, 'at least one away, switch or frustration'],
		['Median first disconnect', firsts.length ? `prompt #${firsts[Math.floor(firsts.length / 2)]}` : '–', 'where the first focus break lands'],
		['Come back → new topic', `${Math.round((100 * afterAwaySwitch) / (afterAway || 1))}%`, 'after a 40-min absence you switch asks'],
		['Worst hour (local)', `${String(worstHour.h).padStart(2, '0')}:00`, `${Math.round(worstHour.rate * 100)}% of prompts are disconnects`]
	];

	// 4. session strips
	let minPrompts = $state(4);
	let SW = $state(900);
	const strips = $derived(F.human.filter((s) => (F.promptsBySession.get(s.id)?.length ?? 0) >= minPrompts).sort((a, b) => a.start.localeCompare(b.start)));
	const sx = $derived(scaleSqrt([0, 900], [150, SW - 10]).clamp(true));
	const mins = (s: string, t: string) => (new Date(t).getTime() - new Date(sessionById.get(s)!.start).getTime()) / 60000;
</script>

<div class="space-y-6">
	<Explain text={sectionText('disconnect')} />

	<div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
		{#each tiles as [k, v, sub]}
			<Card.Root class="gap-1 px-5 py-4">
				<div class="text-xs text-muted-foreground">{k}</div>
				<div class="text-2xl font-semibold tabular-nums">{v}</div>
				<div class="text-xs text-muted-foreground">{sub}</div>
			</Card.Root>
		{/each}
	</div>

	<Card.Root class="gap-2 px-4">
		<div class="px-2 text-sm font-medium">Focus decay: share of prompts that are disconnects, by position in the session</div>
		<div bind:clientWidth={W}>
			<svg width={W} height={H}>
				{#each y.ticks(4) as t}
					<line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="#2c2c2a" />
					<text x={pad.l - 8} y={y(t) + 3} text-anchor="end" font-size="10" fill="#898781">{Math.round(t * 100)}%</text>
				{/each}
				{#each idx as i}
					{@const d = decay[i]}
					{@const cum = [0]}
					{#each KINDS as k, j}
						{@const y0 = KINDS.slice(0, j).reduce((a, kk) => a + d[kk], 0)}
						{#if d[k] > 0}
							<rect x={x(String(i))} y={y(y0 + d[k]) + 1} width={x.bandwidth()} height={Math.max(0, y(y0) - y(y0 + d[k]) - 2)} rx={j === KINDS.length - 1 || !KINDS.slice(j + 1).some((kk) => d[kk] > 0) ? 4 : 0} fill={kindColor(k)} />
						{/if}
					{/each}
					<rect role="presentation" x={x(String(i))} y={pad.t} width={x.bandwidth()} height={H - pad.t - pad.b} fill="transparent"
						onmousemove={(e) => showTip(e, i === MAXI ? `Prompt #${MAXI + 1}+` : `Prompt #${i + 1}`, undefined, [['Disconnects', Math.round(d.any * 100) + '%'], ...KINDS.map((k) => [KIND_LABEL[k], Math.round(d[k] * 100) + '%'] as [string, string]), ['Prompts at this position', String(d.n)]])}
						onmouseleave={hideTip} />
					<text x={x(String(i))! + x.bandwidth() / 2} y={H - 14} text-anchor="middle" font-size="10" fill="#898781">{i === MAXI ? `${MAXI + 1}+` : i + 1}</text>
				{/each}
				{#if cl}<text x={(x(String(cl.at - 1)) ?? 0) + x.bandwidth() / 2} y={y(decay[cl.at - 1].any) - 8} text-anchor="middle" font-size="10" fill="#f0efec">cliff ↓</text>{/if}
				<text x={W / 2} y={H - 1} text-anchor="middle" font-size="10" fill="#898781">prompt number in session</text>
			</svg>
		</div>
		<div class="flex gap-4 px-2 text-xs text-muted-foreground">
			{#each KINDS as k}<span class="flex items-center gap-1.5"><span class="size-2.5 rounded-sm" style="background:{kindColor(k)}"></span>{KIND_LABEL[k]}</span>{/each}
		</div>
	</Card.Root>

	<div class="grid gap-6 lg:grid-cols-[1fr_320px]">
		<Card.Root class="gap-2 px-4">
			<div class="px-2 text-sm font-medium">When you work ({TZ_LABEL}): cell brightness = prompts, outline = disconnect rate ≥ 40%</div>
			<div class="overflow-x-auto px-2">
				<div class="grid min-w-[620px] grid-cols-[36px_repeat(24,1fr)] gap-[2px] text-[10px]">
					<span></span>
					{#each Array(24) as _, h}<span class="text-center text-muted-foreground">{h % 3 === 0 ? h : ''}</span>{/each}
					{#each WD as wd, w}
						<span class="self-center text-muted-foreground">{wd}</span>
						{#each Array(24) as _, h}
							{@const c = cells[w * 24 + h]}
							<button class="aspect-square rounded-[3px] {cell === c ? 'ring-2 ring-foreground' : ''}"
								style="background:{c.n ? ramp(Math.sqrt(c.n / maxN)) : '#222221'};{c.n >= 3 && c.dis / c.n >= 0.4 ? 'outline:2px solid #d95926;outline-offset:-2px' : ''}"
								onmousemove={(e) => showTip(e, `${wd} ${String(h).padStart(2, '0')}:00`, undefined, [['Prompts', String(c.n)], ['Disconnects', c.n ? Math.round((100 * c.dis) / c.n) + '%' : '–']])}
								onmouseleave={hideTip} onclick={() => (cell = c.n ? c : null)} aria-label="{wd} {h}:00"></button>
						{/each}
					{/each}
				</div>
			</div>
		</Card.Root>
		<Card.Root class="gap-2 px-4">
			<div class="px-2 text-sm font-medium">{cell ? `${WD[cell.w]} ${cell.h}:00 · ${cell.n} prompts` : 'Click a cell'}</div>
			<div class="max-h-80 space-y-1 overflow-y-auto">
				{#each cell?.ps ?? [] as p}
					<button class="w-full rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent" onclick={() => openSession(p.s)}>
						<div class="flex items-center gap-1.5 text-muted-foreground">{day(p.t)} · {sessionById.get(p.s)?.project}
							{#each p.kind as k}<span class="size-2 rounded-full" style="background:{kindColor(k)}"></span>{/each}</div>
						<div class="line-clamp-2">{short(p.txt, 160)}</div>
					</button>
				{/each}
			</div>
		</Card.Root>
	</div>

	<Card.Root class="gap-2 px-4">
		<div class="flex flex-wrap items-center gap-2 px-2">
			<span class="text-sm font-medium">Inside each session: every prompt on a time line (√ minutes since start)</span>
			<div class="ml-auto flex items-center gap-1 text-xs">
				min prompts
				{#each [2, 4, 8] as m}<Button size="sm" variant={minPrompts === m ? 'secondary' : 'ghost'} onclick={() => (minPrompts = m)}>{m}+</Button>{/each}
			</div>
		</div>
		<div bind:clientWidth={SW} class="max-h-[560px] overflow-y-auto">
			<svg width={SW} height={strips.length * 22 + 24}>
				{#each [0, 15, 60, 180, 480, 900] as t}
					<line x1={sx(t)} x2={sx(t)} y1={0} y2={strips.length * 22} stroke="#2c2c2a" />
					<text x={sx(t)} y={strips.length * 22 + 14} text-anchor="middle" font-size="10" fill="#898781">{t < 60 ? t + 'm' : t / 60 + 'h'}</text>
				{/each}
				{#each strips as s, r}
					{@const ps = F.promptsBySession.get(s.id) ?? []}
					<g transform="translate(0,{r * 22 + 11})">
						<text x={4} y={4} font-size="10" fill="#c3c2b7" class="cursor-pointer" role="button" tabindex="-1" onclick={() => openSession(s.id)} onkeydown={() => {}}>{day(s.start).slice(5)} {short(s.project, 16)}</text>
						<line x1={sx(0)} x2={sx(mins(s.id, ps.at(-1)!.t))} y1={0} y2={0} stroke="#383835" stroke-width="2" />
						{#each ps as p}
							<circle cx={sx(mins(s.id, p.t))} cy={0} r={p.kind.length ? 5 : 3.5} fill={p.kind.length ? kindColor(p.kind[0]) : '#5a5955'} stroke="#1a1a19" stroke-width="1.5"
								class="cursor-pointer" role="button" tabindex="-1"
								onmousemove={(e) => showTip(e, `${s.project} · #${p.i + 1} · +${Math.round(mins(s.id, p.t))} min`, short(p.txt, 240), p.kind.length ? [['Disconnect', p.kind.map((k) => KIND_LABEL[k]).join(', ')]] : undefined)}
								onmouseleave={hideTip} onclick={() => openSession(s.id)} onkeydown={() => {}} />
						{/each}
					</g>
				{/each}
			</svg>
		</div>
	</Card.Root>
</div>
