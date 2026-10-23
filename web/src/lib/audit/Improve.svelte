<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import Explain from './Explain.svelte';
	import Empty from './Empty.svelte';
	import { sectionText } from './narrative';
	import { ui, FINDINGS } from './store.svelte';

	const IMPROVE = FINDINGS.improve;
	const KEY = 'driftguard-improve';
	const read = () => { try { return JSON.parse(localStorage.getItem(KEY) ?? '{}'); } catch { return {}; } };
	let done = $state<Record<string, boolean>>(read());
	$effect(() => { try { localStorage.setItem(KEY, JSON.stringify(done)); } catch {} });
	let open = $state<string | null>(null);
	const pct = $derived(Math.round((100 * IMPROVE.filter((s) => done[s.id]).length) / (IMPROVE.length || 1)));
	const LINK: Record<string, string> = { 'Focus map': 'disconnect', 'Disconnect map': 'disconnect', 'Project towers (3D)': 'three', 'Monthly volume': 'overview', Tokens: 'tokens' };
</script>

<div class="space-y-6">
	<Explain text={sectionText('improve')} />
	{#if !IMPROVE.length}<Empty />{:else}
	<Card.Root class="gap-2 px-6">
		<div class="flex items-center justify-between text-sm"><span class="font-medium">Progress</span><span class="tabular-nums">{pct}%</span></div>
		<div class="h-2 overflow-hidden rounded-full bg-muted"><div class="h-full rounded-full bg-[#3987e5] transition-all" style="width:{pct}%"></div></div>
	</Card.Root>
	<div class="space-y-2">
		{#each IMPROVE as s, i}
			<Card.Root class="gap-2 px-5 py-4 {done[s.id] ? 'opacity-60' : ''}">
				<div class="flex items-start gap-3">
					<Checkbox class="mt-0.5" checked={!!done[s.id]} onCheckedChange={(v) => (done[s.id] = !!v)} />
					<button class="min-w-0 flex-1 text-left" onclick={() => (open = open === s.id ? null : s.id)}>
						<div class="text-sm font-medium {done[s.id] ? 'line-through' : ''}"><span class="mr-2 text-muted-foreground tabular-nums">{i + 1}.</span>{s.title}</div>
						<p class="mt-1 text-sm text-muted-foreground">{s.short}</p>
						{#if open === s.id || ui.long}<p class="mt-2 text-sm">{s.long}</p>{/if}
					</button>
				</div>
				<div class="flex flex-wrap gap-1.5 pl-7">
					{#each s.evidence ?? [] as e}
						{#if LINK[e]}<button class="rounded-md bg-muted px-2 py-0.5 text-xs hover:bg-accent" onclick={() => (ui.section = LINK[e])}>{e} →</button>
						{:else}<span class="rounded-md bg-muted/60 px-2 py-0.5 text-xs text-muted-foreground">{e}</span>{/if}
					{/each}
				</div>
			</Card.Root>
		{/each}
	</div>
{/if}
</div>
