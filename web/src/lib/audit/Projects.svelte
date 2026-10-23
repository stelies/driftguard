<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { scaleTime } from 'd3';
	import Explain from './Explain.svelte';
	import Empty from './Empty.svelte';
	import { sectionText } from './narrative';
	import { F, ACTIONS, HAS_FINDINGS, FINDINGS, T0, T1, tickFmt, catColor, CATEGORY_ORDER, openProject, showTip, hideTip, openSession, local, fmtTok } from './store.svelte';

	const projs = F.projects
		.map((p) => ({ ...p, ss: F.human.filter((s) => s.project === p.name) }))
		.sort((a, b) => CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category) || b.ss.length - a.ss.length);
	const COLS = [
		{ id: 'keep', title: 'Keep', cats: ['useful-and-good'] },
		{ id: 'part', title: 'Keep a part / ship or kill', cats: ['useful-but-redundant', 'stalled'] },
		{ id: 'kill', title: 'Kill / archive', cats: ['dopamine-build', 'abandoned'] },
		{ id: 'leave', title: 'Leave alone', cats: ['done-no-updates-needed', 'moved-elsewhere', 'unclear', 'unjudged'] }
	];
	let only = $state<string | null>(null);
	let W = $state(900);
	const rowH = 24, pad = { l: 190, r: 16, t: 20 };
	const x = $derived(scaleTime([T0, T1], [pad.l, W - pad.r]));
	const gantt = $derived(projs.filter((p) => p.ss.length && (!only || p.category === only)));
	const A = FINDINGS.answers;
	const QA: [string, string][] = Object.entries(A).filter(([, v]) => typeof v !== 'object' || Array.isArray(v) || v == null)
		.map(([k, v]) => [k.replace(/_/g, ' '), Array.isArray(v) ? v.join(', ') : String(v)] as [string, string]).filter(([, v]) => v);
</script>

<div class="space-y-6">
	<Explain text={sectionText('projects')} />
	{#if !HAS_FINDINGS}<Empty title="Verdicts need the agent pass" />{/if}

	<div class="flex flex-wrap gap-1">
		<Button size="sm" variant={!only ? 'secondary' : 'ghost'} onclick={() => (only = null)}>All</Button>
		{#each CATEGORY_ORDER.filter((c) => projs.some((p) => p.category === c)) as c}
			<Button size="sm" variant={only === c ? 'secondary' : 'ghost'} onclick={() => (only = only === c ? null : c)}>
				<span class="size-2.5 rounded-sm" style="background:{catColor(c)}"></span>{ACTIONS[c].label} {projs.filter((p) => p.category === c).length}
			</Button>
		{/each}
	</div>

	<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
		{#each COLS as col}
			<div class="space-y-2 rounded-2xl bg-muted/40 p-2">
				<div class="px-2 pt-1 text-sm font-medium">{col.title}</div>
				{#each projs.filter((p) => col.cats.includes(p.category) && (!only || p.category === only)) as p}
					<button class="w-full text-left" onclick={() => openProject(p.name)}>
						<Card.Root class="gap-1.5 px-4 py-3 transition-colors hover:bg-accent/50">
							<div class="flex items-center gap-2">
								<span class="size-2.5 shrink-0 rounded-sm" style="background:{catColor(p.category)}"></span>
								<span class="truncate text-sm font-medium">{p.name}</span>
								<span class="ml-auto shrink-0 text-xs text-muted-foreground tabular-nums">{p.ss.length}</span>
							</div>
							<div class="flex flex-wrap gap-1">
								<Badge variant="secondary">{ACTIONS[p.category].label}</Badge>
								{#if p.user_confirmed}<Badge variant="outline">you confirmed</Badge>{/if}
								{#if p.redundant_with}<Badge variant="outline">≈ {p.redundant_with.slice(0, 28)}</Badge>{/if}
							</div>
							<p class="line-clamp-3 text-xs text-muted-foreground">{p.category_reason}</p>
						</Card.Root>
					</button>
				{/each}
			</div>
		{/each}
	</div>

	<Card.Root class="gap-2 px-4">
		<div class="px-2 text-sm font-medium">Timeline: every session is a tick, bars span first → last session</div>
		<div bind:clientWidth={W}>
			<svg width={W} height={gantt.length * rowH + pad.t + 10}>
				{#each x.ticks(6) as t}
					<line x1={x(t)} x2={x(t)} y1={pad.t - 6} y2={gantt.length * rowH + pad.t} stroke="#2c2c2a" />
					<text x={x(t)} y={10} text-anchor="middle" font-size="10" fill="#898781">{tickFmt(t)}</text>
				{/each}
				{#each gantt as p, i}
					{@const ts = p.ss.map((s) => local(s.start).getTime()).sort((a, b) => a - b)}
					{@const y0 = pad.t + i * rowH}
					<text x={pad.l - 8} y={y0 + 15} text-anchor="end" font-size="11" fill="#c3c2b7" class="cursor-pointer" role="button" tabindex="-1" onclick={() => openProject(p.name)} onkeydown={() => {}}>{p.name.slice(0, 26)}</text>
					<rect x={x(new Date(ts[0]))} y={y0 + 6} width={Math.max(4, x(new Date(ts.at(-1)!)) - x(new Date(ts[0])))} height="12" rx="4" fill={catColor(p.category)} fill-opacity="0.35"
						role="button" tabindex="-1" class="cursor-pointer" onclick={() => openProject(p.name)} onkeydown={() => {}}
						onmousemove={(e) => showTip(e, p.name, p.what_it_is, [['Verdict', ACTIONS[p.category].label], ['Sessions', String(p.ss.length)], ['Span', `${new Date(ts[0]).toISOString().slice(0, 10)} → ${new Date(ts.at(-1)!).toISOString().slice(0, 10)}`]])}
						onmouseleave={hideTip} />
					{#each p.ss as s}
						<rect x={x(local(s.start)) - 1.5} y={y0 + 4} width="3" height="16" rx="1" fill={catColor(p.category)} class="cursor-pointer" role="button" tabindex="-1"
							onclick={() => openSession(s.id)} onkeydown={() => {}} onmousemove={(e) => showTip(e, s.title ?? s.id, s.line ?? undefined)} onmouseleave={hideTip} />
					{/each}
				{/each}
			</svg>
		</div>
	</Card.Root>

	{#if QA.length}<Card.Root class="gap-2 px-6">
		<div class="text-sm font-medium">Your poll answers (they override the agent)</div>
		<div class="grid gap-x-6 gap-y-1.5 text-sm md:grid-cols-2">
			{#each QA as [q, a]}<div class="flex gap-3"><span class="w-40 shrink-0 text-muted-foreground">{q}</span><span>{a}</span></div>{/each}
		</div>
	</Card.Root>{/if}
</div>
