<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import * as Table from '$lib/components/ui/table';
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import Explain from './Explain.svelte';
	import { sectionText } from './narrative';
	import { F, ALL, META, HAS_FINDINGS, FINDINGS, AGENT_LABEL, openSession, day, catColor, categoryOf, TZ_LABEL } from './store.svelte';

	const bots = F.sessions.filter((s) => s.bot);
	const botWhy: Record<string, number> = {};
	for (const s of bots) {
		const k = s.n === 0 ? 'no human prompt' : 'auto-generated first prompt (summarizer, title job, test)';
		botWhy[k] = (botWhy[k] ?? 0) + 1;
	}
	const HEUR: [string, string][] = [
		['Real session', 'Has at least one typed prompt and the first prompt is not a summarizer / channel-bot / title / test template.'],
		['Prompt', 'A user message that is not a tool result, meta message, sidechain, slash housekeeping command or continuation summary.'],
		['Away', 'Gap of 40 minutes or more since your previous prompt in the same session.'],
		['Topic switch', '8 or more content words, under 4% word overlap with your previous 3 prompts, not a slash command.'],
		['Frustration', '2+ rage words, or 1 plus caps, or dense caps, or "??" in a short prompt. Pasted plans and terminal output are excluded.'],
		['Motivation / quality', '1 to 5 per session, scored by the agent pass from your prompts.' + (HAS_FINDINGS ? '' : ' Not run yet.')],
		['Local time', `${TZ_LABEL} (this machine's offset at scan time).`],
		['Tokens', 'input + output + cache reads + cache writes per session; 5-hour blocks group assistant turns.']
	];
	let q = $state('');
	let sort = $state<'start' | 'motivation' | 'quality' | 'n'>('start');
	let showBots = $state(false);
	const rows = $derived(
		(showBots ? F.sessions : F.human)
			.filter((s) => !q || `${s.project} ${s.title} ${s.line} ${s.agent} ${s.issues?.join(' ')}`.toLowerCase().includes(q.toLowerCase()))
			.slice().sort((a, b) => (sort === 'start' ? b.start.localeCompare(a.start) : ((b as any)[sort] ?? -1) - ((a as any)[sort] ?? -1)))
	);
</script>

<div class="space-y-6">
	<Explain text={sectionText('diagnostics')} />
	<div class="grid gap-3 md:grid-cols-3">
		<Card.Root class="gap-2 px-5 py-4">
			<div class="text-sm font-medium">Inputs</div>
			<div class="grid grid-cols-[1fr_auto] gap-y-1 text-sm">
				<span class="text-muted-foreground">Transcripts read</span><span class="tabular-nums">{F.sessions.length}</span>
				<span class="text-muted-foreground">Real sessions</span><span class="tabular-nums">{F.human.length}</span>
				<span class="text-muted-foreground">User prompts</span><span class="tabular-nums">{F.prompts.length}</span>
				<span class="text-muted-foreground">Projects judged</span><span class="tabular-nums">{FINDINGS.projects}</span>
				<span class="text-muted-foreground">Example chats</span><span class="tabular-nums">{FINDINGS.chats.length}</span>
				<span class="text-muted-foreground">Built</span><span class="tabular-nums">{META.generated.replace('T', ' ')}</span>
			</div>
		</Card.Root>
		<Card.Root class="gap-2 px-5 py-4">
			<div class="text-sm font-medium">Excluded as auto-generated ({bots.length})</div>
			{#each Object.entries(botWhy) as [k, v]}<div class="flex justify-between text-sm"><span class="text-muted-foreground">{k}</span><span class="tabular-nums">{v}</span></div>{/each}
			<p class="text-xs text-muted-foreground">Summarizer logs, title jobs, test harness runs.</p>
		</Card.Root>
		<Card.Root class="gap-2 px-5 py-4">
			<div class="text-sm font-medium">Agents</div>
			{#each Object.entries(META.summary.counts.by_agent) as [k, v]}<div class="flex justify-between text-sm"><span class="text-muted-foreground">{AGENT_LABEL[k] ?? k}</span><span class="tabular-nums">{v}</span></div>{/each}
			<p class="text-xs text-muted-foreground">driftguard {META.version}. Scan and metrics are deterministic and use no LLM.</p>
		</Card.Root>
	</div>

	<Card.Root class="gap-2 px-6">
		<div class="text-sm font-medium">Heuristics</div>
		{#each HEUR as [k, v]}<div class="grid gap-1 text-sm md:grid-cols-[180px_1fr]"><span class="font-medium">{k}</span><span class="text-muted-foreground">{v}</span></div>{/each}
	</Card.Root>


	<Card.Root class="gap-2 px-4">
		<div class="flex flex-wrap items-center gap-2 px-2">
			<span class="text-sm font-medium">All sessions ({rows.length})</span>
			<Input class="ml-auto h-8 w-56" placeholder="Search project, title, tag…" bind:value={q} />
			<Button size="sm" variant={showBots ? 'secondary' : 'ghost'} onclick={() => (showBots = !showBots)}>Include auto</Button>
		</div>
		<div class="max-h-[600px] overflow-y-auto">
			<Table.Root>
				<Table.Header>
					<Table.Row>
						{#each [['start', 'Date'], ['', 'Agent'], ['', 'Project'], ['', 'Title'], ['n', 'Prompts'], ['motivation', 'Mot'], ['quality', 'Qual']] as [k, l]}
							<Table.Head>{#if k}<button class="font-medium {sort === k ? 'text-foreground' : ''}" onclick={() => (sort = k as any)}>{l}{sort === k ? ' ↓' : ''}</button>{:else}{l}{/if}</Table.Head>
						{/each}
						<Table.Head>Disconnects</Table.Head>
					</Table.Row>
				</Table.Header>
				<Table.Body>
					{#each rows as s}
						<Table.Row class="cursor-pointer {s.bot ? 'opacity-50' : ''}" onclick={() => openSession(s.id)}>
							<Table.Cell class="tabular-nums">{day(s.start)}</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground">{s.agent}</Table.Cell>
							<Table.Cell><span class="mr-1.5 inline-block size-2 rounded-sm" style="background:{catColor(categoryOf(s))}"></span>{s.project}</Table.Cell>
							<Table.Cell class="max-w-xs truncate">{s.title ?? '–'}</Table.Cell>
							<Table.Cell class="tabular-nums">{s.n}</Table.Cell>
							<Table.Cell class="tabular-nums">{s.motivation ?? '–'}</Table.Cell>
							<Table.Cell class="tabular-nums">{s.quality ?? '–'}</Table.Cell>
							<Table.Cell class="text-xs text-muted-foreground tabular-nums">{s.bot ? 'auto' : `${s.aways ?? 0}/${s.rage ?? 0}/${s.switches ?? 0}`}</Table.Cell>
						</Table.Row>
					{/each}
				</Table.Body>
			</Table.Root>
		</div>
	</Card.Root>
</div>
