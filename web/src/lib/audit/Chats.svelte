<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import Explain from './Explain.svelte';
	import Empty from './Empty.svelte';
	import { sectionText } from './narrative';
	import { FINDINGS, sessionById, openSession } from './store.svelte';
	const COACH = FINDINGS.coach;

	const kindOf = (w: string) =>
		/best|good|clear|strong|structured/i.test(w) ? 'best' : /rage|frustrat|sarcas|trust|annoy/i.test(w) ? 'frustration' : /drift|scope|creep|pivot/i.test(w) ? 'drift' : 'other';
	const chats = FINDINGS.chats.map((c) => ({ ...c, kind: kindOf(c.why_notable) })).sort((a, b) => a.date.localeCompare(b.date));
	const FILTERS = [['all', 'All'], ['best', 'Best'], ['frustration', 'Frustration'], ['drift', 'Drift'], ['other', 'Other']] as const;
	let f = $state<string>('all');
	let open = $state<Record<number, boolean>>({});
	const shown = $derived(chats.filter((c) => f === 'all' || c.kind === f));
	const rewrite = (u: string) => COACH.find((c) => u.slice(0, 30).toLowerCase().includes(c.bad.slice(0, 20).toLowerCase()) || c.bad.slice(0, 30).toLowerCase().includes(u.slice(0, 20).toLowerCase()));
	const BADGE: Record<string, 'default' | 'destructive' | 'secondary' | 'outline'> = { best: 'default', frustration: 'destructive', drift: 'secondary', other: 'outline' };
</script>

<div class="space-y-6">
	<Explain text={sectionText('chats')} />
	{#if !chats.length}<Empty title="No example chats yet" />{:else}
	<div class="flex flex-wrap gap-1">
		{#each FILTERS as [id, l]}
			<Button size="sm" variant={f === id ? 'secondary' : 'ghost'} onclick={() => (f = id)}>{l} {id === 'all' ? chats.length : chats.filter((c) => c.kind === id).length}</Button>
		{/each}
	</div>
	<div class="mx-auto max-w-3xl space-y-8">
		{#each shown as c, i}
			{@const rw = c.better_prompt ? { better: c.better_prompt } : rewrite(c.user)}
			<div class="space-y-3">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<Badge variant={BADGE[c.kind]}>{c.kind}</Badge>{c.date?.slice(0, 10)} · {c.project}
					{#if sessionById.has(c.session)}<button class="ml-auto underline-offset-4 hover:underline" onclick={() => openSession(c.session)}>open session</button>{/if}
				</div>
				<div class="flex justify-end">
					<div class="max-w-[85%] rounded-2xl bg-muted px-4 py-3 text-sm whitespace-pre-wrap">{c.user}</div>
				</div>
				<button class="block w-full text-left" onclick={() => (open[i] = !open[i])}>
					<div class="text-sm leading-relaxed {open[i] ? '' : 'line-clamp-2'}">
						<span class="mr-1 text-xs font-medium text-muted-foreground">Claude</span>{c.assistant_gist}
					</div>
				</button>
				<Card.Root class="gap-1 px-4 py-3">
					<div class="text-xs font-medium">What to take from it</div>
					<p class="text-sm text-muted-foreground">{c.why_notable}</p>
					{#if rw}
						<div class="mt-1 text-xs font-medium">Better prompt</div>
						<p class="font-mono text-xs whitespace-pre-wrap">{rw.better}</p>
					{/if}
				</Card.Root>
			</div>
		{/each}
	</div>
{/if}
</div>
