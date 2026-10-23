<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { scaleTime, scaleLog, scaleBand, scaleLinear } from 'd3';
	import Explain from './Explain.svelte';
	import Empty from './Empty.svelte';
	import { sectionText } from './narrative';
	import { F, FINDINGS, HAS_FINDINGS, T0, T1, tickFmt, sessionById, kindColor, KIND_LABEL, showTip, hideTip, openSession, short, day } from './store.svelte';
	const COACH = FINDINGS.coach;
	// Best prompts: first prompt of the highest-quality scored sessions.
	const BEST = F.human.filter((s) => (s.quality ?? 0) >= 4 && F.promptsBySession.get(s.id)?.length).sort((a, b) => (b.quality ?? 0) - (a.quality ?? 0)).slice(0, 6)
		.map((s) => ({ date: s.start.slice(0, 10), project: s.project, bad: short(F.promptsBySession.get(s.id)![0].txt, 300), why: s.line ?? '' }));

	let W = $state(900);
	const H = 300, pad = { l: 44, r: 14, t: 10, b: 24 };
	const x = $derived(scaleTime([T0, T1], [pad.l, W - pad.r]));
	const y = scaleLog([10, 60000], [H - pad.b, pad.t]).clamp(true);
	let only = $state<string | null>(null);
	let skillOnly = $state(false);
	const pts = $derived(F.prompts.filter((p) => (!only || p.kind.includes(only)) && (!skillOnly || p.skill)));
	const jitter = (s: string) => ((s.charCodeAt(0) * 7 + s.charCodeAt(5)) % 11) - 5;

	const tagCount: Record<string, number> = {};
	for (const s of F.human) for (const t of s.issues ?? []) tagCount[t] = (tagCount[t] ?? 0) + 1;
	const tags = Object.entries(tagCount).sort((a, b) => b[1] - a[1]);
	const GOOD = new Set(['good-spec', 'clear-constraints', 'iterative-good']);
	let tag = $state<string | null>(null);
	const tagSessions = $derived(tag ? F.human.filter((s) => s.issues?.includes(tag!)) : []);
	const tx = scaleLinear([0, Math.max(1, ...tags.map((t) => t[1]))], [0, 100]);
	let flipped = $state<Record<number, boolean>>({});
</script>

<div class="space-y-6">
	<Explain text={sectionText('prompts')} />

	<Card.Root class="gap-2 px-4">
		<div class="flex flex-wrap items-center gap-2 px-2">
			<span class="text-sm font-medium">Every prompt typed: length over time</span>
			<div class="ml-auto flex flex-wrap gap-1">
				<Button size="sm" variant={!only ? 'secondary' : 'ghost'} onclick={() => (only = null)}>All</Button>
				{#each Object.keys(KIND_LABEL) as k}
					<Button size="sm" variant={only === k ? 'secondary' : 'ghost'} onclick={() => (only = only === k ? null : k)}>
						<span class="size-2 rounded-full" style="background:{kindColor(k)}"></span>{KIND_LABEL[k]}
					</Button>
				{/each}
				<Button size="sm" variant={skillOnly ? 'secondary' : 'ghost'} onclick={() => (skillOnly = !skillOnly)}>Skill-led (/…)</Button>
			</div>
		</div>
		<div bind:clientWidth={W}>
			<svg width={W} height={H}>
				{#each [10, 100, 1000, 10000] as t}
					<line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="#2c2c2a" />
					<text x={pad.l - 8} y={y(t) + 3} text-anchor="end" font-size="10" fill="#898781">{t >= 1000 ? t / 1000 + 'k' : t}</text>
				{/each}
				<text x={4} y={pad.t + 4} font-size="10" fill="#898781">chars</text>
				{#each x.ticks(6) as t}<text x={x(t)} y={H - 6} text-anchor="middle" font-size="10" fill="#898781">{tickFmt(t)}</text>{/each}
				{#each pts as p}
					<circle cx={x(new Date(p.t)) + jitter(p.s)} cy={y(Math.max(10, p.len))} r="4.5" fill={p.kind.length ? kindColor(p.kind[0]) : '#5a5955'}
						fill-opacity={p.kind.length ? 0.9 : 0.55} stroke="#1a1a19" stroke-width="1.5" class="cursor-pointer" role="button" tabindex="-1"
						onmousemove={(e) => showTip(e, `${day(p.t)} · ${sessionById.get(p.s)?.project} · #${p.i + 1}`, short(p.txt, 260), [['Length', p.len + ' chars'], ['Kind', p.kind.map((k) => KIND_LABEL[k]).join(', ') || 'on-topic']])}
						onmouseleave={hideTip} onclick={() => openSession(p.s)} onkeydown={() => {}} />
				{/each}
			</svg>
		</div>
		<p class="px-2 text-xs text-muted-foreground">Gray = on-topic. Long dots near 10k+ are pasted specs/logs. A wall of short colored dots means rapid-fire fixing.</p>
	</Card.Root>

	<div class="grid gap-6 lg:grid-cols-2">
		<Card.Root class="gap-2 px-6">
			<div class="text-sm font-medium">Prompt issue tags (sessions)</div>
			<p class="text-xs text-muted-foreground">Click a tag to list its sessions. Blue = good habit, orange = bad habit.</p>
			{#each tags as [t, n]}
				<button class="group flex items-center gap-3 text-left text-sm" onclick={() => (tag = tag === t ? null : t)}>
					<span class="w-32 shrink-0 truncate {tag === t ? 'font-medium' : 'text-muted-foreground'}">{t}</span>
					<span class="h-4 rounded-[4px] transition-all group-hover:brightness-125" style="width:{tx(n)}%;background:{GOOD.has(t) ? '#3987e5' : '#d95926'}"></span>
					<span class="text-xs tabular-nums">{n}</span>
				</button>
			{/each}
		</Card.Root>
		<Card.Root class="gap-2 px-6">
			<div class="text-sm font-medium">{tag ? `Sessions tagged “${tag}”` : 'Pick a tag'}</div>
			<div class="max-h-96 space-y-1 overflow-y-auto">
				{#each tagSessions as s}
					<button class="flex w-full flex-col rounded-md px-2 py-1.5 text-left hover:bg-accent" onclick={() => openSession(s.id)}>
						<span class="text-sm">{s.title ?? s.id}</span>
						<span class="text-xs text-muted-foreground">{day(s.start)} · {s.project} · quality {s.quality ?? '–'}/5</span>
					</button>
				{:else}<p class="text-sm text-muted-foreground">Tags come from the agent pass reading every session.</p>{/each}
			</div>
		</Card.Root>
	</div>

	{#if !HAS_FINDINGS}<Empty title="Coaching and tags need the agent pass" />{:else}
	<div>
		<h2 class="mb-1 text-lg font-semibold">Coaching: weakest prompts, rewritten</h2>
		<p class="mb-3 text-sm text-muted-foreground">Click a card to flip between what you sent and what would have worked.</p>
		<div class="grid gap-3 md:grid-cols-2">
			{#each COACH as c, i}
				<button class="text-left" onclick={() => (flipped[i] = !flipped[i])}>
					<Card.Root class="h-full gap-2 px-5 py-4 transition-colors hover:bg-accent/40">
						<div class="flex items-center gap-2 text-xs text-muted-foreground">
							<Badge variant={flipped[i] ? 'default' : 'destructive'}>{flipped[i] ? 'Better' : 'Sent'}</Badge>{c.date} · {c.project}
						</div>
						<p class="font-mono text-sm whitespace-pre-wrap">{flipped[i] ? c.better : c.bad}</p>
						<p class="text-xs text-muted-foreground">{c.why}</p>
					</Card.Root>
				</button>
			{/each}
		</div>
		<h2 class="mt-6 mb-3 text-lg font-semibold">Best prompts: do more of these</h2>
		<div class="grid gap-3 md:grid-cols-3">
			{#each BEST as c}
				<Card.Root class="gap-2 px-5 py-4">
					<div class="text-xs text-muted-foreground">{c.date} · {c.project}</div>
					<p class="font-mono text-sm">{c.bad}</p>
					<p class="text-xs text-muted-foreground">{c.why}</p>
				</Card.Root>
			{/each}
		</div>
	</div>
	{/if}
</div>
