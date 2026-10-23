<script lang="ts">
	import * as Dialog from '$lib/components/ui/dialog';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import {
		ui, sessionById, F, ACTIONS, fmtTok, AGENT_LABEL, catColor, kindColor, KIND_LABEL, local, day, openSession, openProject, projectOf
	} from './store.svelte';

	const s = $derived(ui.session ? sessionById.get(ui.session) : null);
	const ps = $derived(ui.session ? (F.promptsBySession.get(ui.session) ?? []) : []);
	const p = $derived(ui.project ? F.projects.find((x) => x.name === ui.project) : null);
	const pSessions = $derived(p ? F.human.filter((x) => projectOf(x)?.name === p.name).sort((a, b) => a.start.localeCompare(b.start)) : []);
	const daySessions = $derived(ui.day ? F.human.filter((x) => day(x.start) === ui.day) : []);
	const fmt = (t: string) => local(t).toISOString().slice(0, 16).replace('T', ' ');
	const score = (v: number | null) => (v == null ? '–' : '●'.repeat(v) + '○'.repeat(5 - v));
	let filter = $state<string | null>(null);
	const shown = $derived(filter ? ps.filter((x) => x.kind.includes(filter!)) : ps);
</script>

<Dialog.Root open={!!s} onOpenChange={(o) => !o && (ui.session = null)}>
	<Dialog.Content class="max-h-[85dvh] overflow-y-auto sm:max-w-3xl">
		{#if s}
			<Dialog.Header>
				<Dialog.Title>{s.title ?? 'Untitled session'}</Dialog.Title>
				<Dialog.Description>
					{s.project} · {fmt(s.start)} → {fmt(s.end).slice(11)} · {s.n} prompts · {s.tools} tool calls · {fmtTok(s.tok)} tokens · {AGENT_LABEL[s.agent] ?? s.agent}
				</Dialog.Description>
			</Dialog.Header>
			<div class="grid gap-3 sm:grid-cols-3">
				<div class="rounded-lg bg-muted/50 p-3"><div class="text-xs text-muted-foreground">Motivation</div><div class="mt-1 tracking-widest">{score(s.motivation)}</div></div>
				<div class="rounded-lg bg-muted/50 p-3"><div class="text-xs text-muted-foreground">Prompt quality</div><div class="mt-1 tracking-widest">{score(s.quality)}</div></div>
				<div class="rounded-lg bg-muted/50 p-3">
					<div class="text-xs text-muted-foreground">Disconnects</div>
					<div class="mt-1 text-sm tabular-nums">{s.aways ?? 0} away · {s.rage ?? 0} frustration · {s.switches ?? 0} switch</div>
				</div>
			</div>
			{#if s.line}<p class="text-sm">{s.line}</p>{/if}
			{#if s.evidence}<blockquote class="border-l-2 pl-3 text-sm text-muted-foreground italic">“{s.evidence}”</blockquote>{/if}
			{#if s.issues?.length}
				<div class="flex flex-wrap gap-1.5">{#each s.issues as i}<Badge variant="outline">{i}</Badge>{/each}</div>
			{/if}
			<div class="flex flex-wrap items-center gap-1.5 text-xs">
				<span class="text-muted-foreground">Filter prompts:</span>
				<Button size="sm" variant={filter ? 'ghost' : 'secondary'} onclick={() => (filter = null)}>All {ps.length}</Button>
				{#each Object.keys(KIND_LABEL) as k}
					<Button size="sm" variant={filter === k ? 'secondary' : 'ghost'} onclick={() => (filter = filter === k ? null : k)}>
						<span class="size-2 rounded-full" style="background:{kindColor(k)}"></span>{KIND_LABEL[k]} {ps.filter((x) => x.kind.includes(k)).length}
					</Button>
				{/each}
			</div>
			<ol class="space-y-2">
				{#each shown as x}
					<li class="rounded-lg border border-border/20 p-3">
						<div class="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
							<span class="font-medium text-foreground">#{x.i + 1}</span>
							<span class="tabular-nums">{fmt(x.t).slice(11)}</span>
							{#if x.gap}<span>+{Math.round(x.gap)} min</span>{/if}
							<span>{x.len} chars</span>
							{#each x.kind as k}<span class="flex items-center gap-1"><span class="size-2 rounded-full" style="background:{kindColor(k)}"></span>{KIND_LABEL[k]}</span>{/each}
						</div>
						<p class="whitespace-pre-wrap text-sm break-words">{x.txt}</p>
					</li>
				{:else}
					<li class="text-sm text-muted-foreground">No F.human prompts (auto-generated session).</li>
				{/each}
			</ol>
			<p class="text-xs text-muted-foreground">Session id {s.id}</p>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<Dialog.Root open={!!p} onOpenChange={(o) => !o && (ui.project = null)}>
	<Dialog.Content class="max-h-[85dvh] overflow-y-auto sm:max-w-2xl">
		{#if p}
			<Dialog.Header>
				<Dialog.Title class="flex items-center gap-2">
					<span class="size-3 rounded-sm" style="background:{catColor(p.category)}"></span>{p.name}
				</Dialog.Title>
				<Dialog.Description>{p.what_it_is}</Dialog.Description>
			</Dialog.Header>
			<div class="flex flex-wrap gap-2">
				<Badge>{ACTIONS[p.category]?.label ?? p.category}</Badge>
				<Badge variant="secondary">{ACTIONS[p.category]?.verb}</Badge>
				{#if p.user_confirmed}<Badge variant="outline">you confirmed</Badge>{/if}
				<Badge variant="outline">{p.first?.slice(0, 10)} → {p.last?.slice(0, 10)}</Badge>
				<Badge variant="outline">{fmtTok(p.tokens)} tokens</Badge>
			</div>
			{#if p.category_reason}<p class="text-sm">{p.category_reason}</p>{/if}
			{#if p.redundant_with}<p class="text-sm text-muted-foreground">Already exists: <span class="text-foreground">{p.redundant_with}</span></p>{/if}
			{#if p.status_last_seen}<p class="text-sm text-muted-foreground">Last seen: {p.status_last_seen}</p>{/if}
			{#if p.drift?.length}
				<h4 class="text-sm font-medium">Drift</h4>
				{#each p.drift as d}
					<div class="rounded-lg bg-muted/50 p-3 text-sm">
						<div class="text-xs text-muted-foreground">{d.date?.slice(0, 10)}</div>
						<div>{d.from} → <span class="font-medium">{d.to}</span></div>
						<div class="mt-1 text-muted-foreground italic">“{d.quote}”</div>
					</div>
				{/each}
			{/if}
			<h4 class="text-sm font-medium">Sessions ({pSessions.length})</h4>
			<div class="space-y-1">
				{#each pSessions as x}
					<button class="flex w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent" onclick={() => openSession(x.id)}>
						<span class="w-24 shrink-0 text-xs text-muted-foreground tabular-nums">{day(x.start)}</span>
						<span class="truncate">{x.title ?? x.line ?? x.id}</span>
						<span class="ml-auto shrink-0 text-xs text-muted-foreground">{x.n} prompts</span>
					</button>
				{:else}<p class="text-sm text-muted-foreground">No F.human sessions mapped.</p>{/each}
			</div>
		{/if}
	</Dialog.Content>
</Dialog.Root>

<Dialog.Root open={!!ui.day} onOpenChange={(o) => !o && (ui.day = null)}>
	<Dialog.Content class="max-h-[85dvh] overflow-y-auto sm:max-w-2xl">
		<Dialog.Header>
			<Dialog.Title>{ui.day}</Dialog.Title>
			<Dialog.Description>{daySessions.length} real sessions that day</Dialog.Description>
		</Dialog.Header>
		{#each daySessions as x}
			<button class="flex w-full flex-col gap-1 rounded-lg border border-border/20 p-3 text-left hover:bg-accent" onclick={() => openSession(x.id)}>
				<div class="flex items-center gap-2 text-sm font-medium">
					<span class="size-2.5 rounded-sm" style="background:{catColor(projectOf(x)?.category ?? 'unclear')}"></span>{x.title ?? x.id}
				</div>
				<div class="text-xs text-muted-foreground">
					{x.project} · motivation {x.motivation ?? '–'}/5 · quality {x.quality ?? '–'}/5 · {x.n} prompts
				</div>
				{#if x.evidence}<div class="text-xs italic text-muted-foreground">“{x.evidence}”</div>{/if}
			</button>
		{/each}
		{#if daySessions.length}
			<Button variant="ghost" size="sm" onclick={() => { const n = projectOf(daySessions[0])?.name; if (n) openProject(n); }}>Open first project</Button>
		{/if}
	</Dialog.Content>
</Dialog.Root>
