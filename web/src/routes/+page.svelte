<script lang="ts">
	import { Switch } from '$lib/components/ui/switch';
	import { Badge } from '$lib/components/ui/badge';
	import { Separator } from '$lib/components/ui/separator';
	import * as ToggleGroup from '$lib/components/ui/toggle-group';
	import { ui, SECTIONS, F, META, AGENTS, AGENT_LABEL, AGENT_COLOR, EMPTY, filterKey, rangeLabel } from '$lib/audit/store.svelte';
	import Overview from '$lib/audit/Overview.svelte';
	import Motivation from '$lib/audit/Motivation.svelte';
	import Prompts from '$lib/audit/Prompts.svelte';
	import Disconnect from '$lib/audit/Disconnect.svelte';
	import Three from '$lib/audit/Three.svelte';
	import Projects from '$lib/audit/Projects.svelte';
	import Drift from '$lib/audit/Drift.svelte';
	import Chats from '$lib/audit/Chats.svelte';
	import Improve from '$lib/audit/Improve.svelte';
	import Tokens from '$lib/audit/Tokens.svelte';
	import Setup from '$lib/audit/Setup.svelte';
	import Diagnostics from '$lib/audit/Diagnostics.svelte';
	import Dialogs from '$lib/audit/Dialogs.svelte';
	import {
		LayoutDashboard, HeartPulse, MessageSquareText, BrainCircuit, Box, FolderKanban, Waypoints, MessagesSquare, Target, Stethoscope, Coins, Wrench, ShieldCheck
	} from '@lucide/svelte';

	const ICONS: Record<string, typeof Box> = {
		overview: LayoutDashboard, motivation: HeartPulse, prompts: MessageSquareText, disconnect: BrainCircuit, three: Box,
		projects: FolderKanban, drift: Waypoints, chats: MessagesSquare, improve: Target, tokens: Coins, setup: Wrench, diagnostics: Stethoscope
	};
	const VIEWS: Record<string, any> = { overview: Overview, motivation: Motivation, prompts: Prompts, disconnect: Disconnect, three: Three, projects: Projects, drift: Drift, chats: Chats, improve: Improve, tokens: Tokens, setup: Setup, diagnostics: Diagnostics };

	// The hash router owns location.hash, so the open section is remembered in localStorage instead.
	const KEY = 'driftguard-section';
	ui.section = SECTIONS[0].id;
	// Embedded (e.g. the live demo on the landing page) always starts on the first section.
	const embedded = typeof window !== 'undefined' && window.self !== window.top;
	try {
		const saved = embedded ? null : localStorage.getItem(KEY);
		if (saved && SECTIONS.some((s) => s.id === saved)) ui.section = saved;
	} catch {}
	$effect(() => {
		if (embedded) return;
		try { localStorage.setItem(KEY, ui.section); } catch {}
	});
	const go = (id: string) => {
		ui.section = id;
		scrollTo({ top: 0 });
	};
	const View = $derived(VIEWS[ui.section]);
	const current = $derived(SECTIONS.find((s) => s.id === ui.section));
	// Empty selection means "all agents".
	const selected = $derived(ui.agents.length ? ui.agents : AGENTS);
	const setAgents = (v: string[]) => (ui.agents = v.length === AGENTS.length || v.length === 0 ? [] : v);
</script>

<div class="flex min-h-dvh flex-col md:flex-row">
	<aside
		class="sticky top-2 z-10 mx-2 mt-2 flex flex-col rounded-2xl bg-muted/60 p-2 shadow-md backdrop-blur-xl md:h-[calc(100dvh-1.125rem)] md:w-72"
	>
		<div class="flex items-center gap-2 px-2 pt-1 pb-3">
			<div class="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground"><ShieldCheck class="size-4" /></div>
			<div class="min-w-0">
				<div class="truncate text-sm font-semibold">driftguard</div>
				<div class="truncate text-xs text-muted-foreground">{F.human.length} real sessions · {F.prompts.length} prompts</div>
			</div>
		</div>
		{#if AGENTS.length > 1}
			<div class="px-2 pb-2">
				<div class="pb-1 text-[11px] text-muted-foreground">Agents</div>
				<ToggleGroup.Root type="multiple" variant="outline" size="sm" value={selected} onValueChange={setAgents} class="flex-wrap justify-start">
					{#each AGENTS as a}
						<ToggleGroup.Item value={a} class="text-xs"><span class="mr-1 size-2 rounded-full" style="background:{AGENT_COLOR[a]}"></span>{AGENT_LABEL[a] ?? a}</ToggleGroup.Item>
					{/each}
				</ToggleGroup.Root>
			</div>
		{/if}
		<nav class="flex gap-1 overflow-x-auto md:flex-col md:overflow-y-auto">
			{#each SECTIONS as s}
				{@const Icon = ICONS[s.id]}
				<button
					class="flex shrink-0 items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition-colors hover:bg-accent {ui.section === s.id
						? 'bg-accent font-medium text-accent-foreground'
						: 'text-muted-foreground'}"
					onclick={() => go(s.id)}
				>
					<Icon class="size-4" />
					<span class="whitespace-nowrap">{s.label}</span>
				</button>
			{/each}
		</nav>
		<div class="mt-auto hidden md:block">
			<Separator class="my-2" />
			<label class="flex items-center justify-between rounded-lg px-2.5 py-2 text-sm">
				<span>Long explanations</span>
				<Switch bind:checked={ui.long} />
			</label>
			<div class="px-2.5 pb-1 text-[11px] text-muted-foreground">Built {META.generated.replace('T', ' ')} · v{META.version}</div>
		</div>
	</aside>

	<main class="min-w-0 flex-1 px-4 py-6 md:px-10">
		<div class="mx-auto max-w-6xl">
			<div class="mb-6 flex flex-wrap items-center gap-3">
				<h1 class="text-2xl font-semibold tracking-tight">{current?.label}</h1>
				{#if !EMPTY}<Badge variant="secondary">{rangeLabel}</Badge>{/if}
				<label class="ml-auto flex items-center gap-2 text-sm md:hidden">Long <Switch bind:checked={ui.long} /></label>
			</div>
			{#if EMPTY}
				<div class="rounded-xl border border-dashed p-8 text-sm text-muted-foreground">No scan data in this report. Run <code>driftguard scan</code>, then <code>driftguard report</code>.</div>
			{:else}
				{#key ui.section + '|' + filterKey()}
					<View />
				{/key}
			{/if}
		</div>
	</main>
</div>

{#if ui.tip}
	<div
		class="pointer-events-none fixed z-[100] max-w-sm rounded-md border border-border/20 bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md"
		style="left:{Math.min(ui.tip.x + 14, innerWidth - 380)}px;top:{ui.tip.y + 14}px"
	>
		<div class="font-medium">{ui.tip.title}</div>
		{#if ui.tip.rows}
			<div class="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
				{#each ui.tip.rows as [k, v]}<span class="text-muted-foreground">{k}</span><span class="tabular-nums">{v}</span>{/each}
			</div>
		{/if}
		{#if ui.tip.body}<div class="mt-1 whitespace-pre-wrap text-muted-foreground">{ui.tip.body}</div>{/if}
	</div>
{/if}

<Dialogs />
