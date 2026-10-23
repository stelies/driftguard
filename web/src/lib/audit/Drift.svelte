<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceX, forceY, drag, select } from 'd3';
	import { untrack } from 'svelte';
	import Explain from './Explain.svelte';
	import Empty from './Empty.svelte';
	import { sectionText } from './narrative';
	import { F, ACTIONS, catColor, openProject, showTip, hideTip, short } from './store.svelte';

	type N = { id: string; label: string; kind: 'project' | 'target'; c: string; x?: number; y?: number; fx?: number | null; fy?: number | null; project?: string };
	type L = { source: string | N; target: string | N; quote: string; date: string; from: string };
	const nodes: N[] = [];
	const links: L[] = [];
	for (const p of F.projects) {
		if (!p.drift?.length) continue;
		nodes.push({ id: p.name, label: p.name, kind: 'project', c: catColor(p.category), project: p.name });
		for (const d of p.drift) {
			const id = p.name + '→' + d.to;
			nodes.push({ id, label: d.to, kind: 'target', c: '#5a5955', project: p.name });
			links.push({ source: p.name, target: id, quote: d.quote, date: d.date, from: d.from });
		}
	}
	let W = $state(900);
	const H = 560;
	let tick = $state(0);
	let sel = $state<L | null>(null);
	$effect(() => {
		const w = W;
		const sim = untrack(() => forceSimulation(nodes as any)
			.force('link', forceLink(links as any).id((d: any) => d.id).distance(90))
			.force('charge', forceManyBody().strength(-260))
			.force('center', forceCenter(w / 2, H / 2))
			.force('collide', forceCollide(46))
			.force('x', forceX(w / 2).strength(0.06))
			.force('y', forceY(H / 2).strength(0.1))
			.on('tick', () => {
				for (const n of nodes) {
					n.x = Math.max(70, Math.min(w - 70, n.x ?? 0));
					n.y = Math.max(30, Math.min(H - 50, n.y ?? 0));
				}
				tick++;
			}));
		return () => sim.stop();
	});
	function draggable(el: SVGGElement, n: N) {
		const sim = () => (n as any);
		select(el).datum(n).call(drag<SVGGElement, N>()
			.on('start', (e) => { n.fx = n.x; n.fy = n.y; })
			.on('drag', (e) => { n.fx = e.x; n.fy = e.y; n.x = e.x; n.y = e.y; tick++; })
			.on('end', () => { n.fx = null; n.fy = null; }) as any);
	}
	const S = (l: L) => l.source as N, T = (l: L) => l.target as N;
	const wrap = (s: string) => { const w = s.split(' '); const out: string[] = []; let line = ''; for (const x of w) { if ((line + ' ' + x).length > 22) { out.push(line); line = x; } else line = (line + ' ' + x).trim(); } out.push(line); return out.slice(0, 3); };
</script>

<div class="space-y-6">
	<Explain text={sectionText('drift')} />
	{#if !links.length}<Empty title="No drift recorded yet" hint="Drift (a project turning into something else) is detected by the agent pass from your own prompts. Run /driftguard, then rebuild this report." />{:else}
	<div class="grid gap-6 lg:grid-cols-[1fr_320px]">
		<Card.Root class="gap-2 overflow-hidden px-0 py-0">
			<div bind:clientWidth={W} class="bg-[#1a1a19]">
				<svg width={W} height={H}>
					{#key tick}
						{#each links as l}
							{#if S(l).x != null}
								<line x1={S(l).x} y1={S(l).y} x2={T(l).x} y2={T(l).y} stroke={sel === l ? '#f0efec' : '#5a5955'} stroke-width={sel === l ? 3 : 2}
									class="cursor-pointer" role="button" tabindex="-1" onclick={() => (sel = l)} onkeydown={() => {}}
									onmousemove={(e) => showTip(e, `${S(l).label} drifted (${l.date?.slice(0, 10)})`, `“${short(l.quote, 200)}”`)} onmouseleave={hideTip} />
							{/if}
						{/each}
					{/key}
					{#each nodes as n (n.id)}
						<g use:draggable={n} transform="translate({(tick, n.x ?? 0)},{(tick, n.y ?? 0)})" class="cursor-grab">
							{#if n.kind === 'project'}
								<circle r="22" fill={n.c} stroke="#1a1a19" stroke-width="2" role="button" tabindex="-1" ondblclick={() => openProject(n.id)} onkeydown={() => {}}
									onmousemove={(e) => showTip(e, n.label, 'Drag to move · double-click to open project')} onmouseleave={hideTip} />
								<text y="38" text-anchor="middle" font-size="12" font-weight="600" fill="#f0efec">{n.label.slice(0, 24)}</text>
							{:else}
								<rect x="-8" y="-8" width="16" height="16" rx="4" fill="#5a5955" stroke="#1a1a19" stroke-width="2" />
								{#each wrap(n.label) as ln, i}<text y={24 + i * 12} text-anchor="middle" font-size="10" fill="#c3c2b7">{ln}</text>{/each}
							{/if}
						</g>
					{/each}
				</svg>
			</div>
		</Card.Root>
		<Card.Root class="gap-3 px-5">
			<div class="text-sm font-medium">{sel ? S(sel).label : 'Click an edge'}</div>
			{#if sel}
				<div class="text-xs text-muted-foreground">{sel.date?.slice(0, 10)}</div>
				<div class="text-sm">{sel.from} → <span class="font-medium">{T(sel).label}</span></div>
				<blockquote class="border-l-2 pl-3 text-sm text-muted-foreground italic">“{sel.quote}”</blockquote>
				{@const p = F.projects.find((x) => x.name === S(sel!).id)}
				{#if p}<div class="text-xs">Verdict: {ACTIONS[p.category]?.label}: {p.category_reason}</div>{/if}
			{:else}
				{#each links as l}
					<button class="rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent" onclick={() => (sel = l)}>
						<span class="font-medium">{(l.source as N).label ?? l.source}</span>: {short(l.quote, 90)}
					</button>
				{/each}
			{/if}
		</Card.Root>
	</div>
{/if}
</div>
