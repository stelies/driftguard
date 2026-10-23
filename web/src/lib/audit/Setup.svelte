<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { CircleCheck, CircleAlert } from '@lucide/svelte';
	import Explain from './Explain.svelte';
	import { sectionText } from './narrative';
	import { META, ui, AGENT_LABEL } from './store.svelte';

	const s = META.setup;
	type Item = { name: string; ok: boolean; status: string; why: string; fix: string };
	const items: Item[] = [
		{ name: 'Rules file (CLAUDE.md)', ok: !!s.claude_md, status: s.claude_md ? 'present' : 'missing',
			why: 'A rules file is read at the start of every session. It is where your agent learns your stack, your don\'ts and your definition of done, so you stop repeating them.',
			fix: 'Create ~/.claude/CLAUDE.md with 10 lines: who you are, your main projects, and 3 rules you keep typing ("never push unless asked", "ask before big refactors"). `driftguard guard` can draft a drift-guard block for you.' },
		{ name: 'Skills', ok: (s.skills ?? 0) > 0, status: `${s.skills ?? 0} installed`,
			why: 'Skills are reusable instructions the agent loads on demand: a review checklist, a deploy routine, your writing style. Without them every session starts from zero.',
			fix: 'Pick the one task you explain most often and save it as ~/.claude/skills/<name>/SKILL.md. Start with one; more than a few dozen mostly adds noise.' },
		{ name: 'Hooks', ok: !!s.hooks, status: s.hooks ? 'configured' : 'none',
			why: 'Hooks run your own commands at fixed moments (before a tool call, after an edit). They are the only way to make a rule certain instead of "usually".',
			fix: 'Add a hook in ~/.claude/settings.json for the one mistake that keeps coming back, for example blocking `git push` or running tests after edits.' },
		{ name: 'Permission allow-list', ok: (s.permissions_allow ?? 0) > 0, status: `${s.permissions_allow ?? 0} rules`,
			why: 'Without an allow-list the agent asks before every harmless command, which breaks your focus. Too broad and it can do damage unasked.',
			fix: 'Allow read-only commands you approve every time (ls, git status, test runners) and keep writes and network on ask.' },
		{ name: 'MCP servers', ok: (s.mcp_servers ?? 0) > 0, status: `${s.mcp_servers ?? 0} configured`,
			why: 'MCP servers connect the agent to tools and data (browser, database, docs). They are optional; each one also costs context tokens every session.',
			fix: 'Only add one if you do the same manual copy-paste weekly. Remove ones you have not used in a month.' },
		{ name: 'Code graph (graphify)', ok: !!s.graphify, status: s.graphify ? 'installed' : 'not installed',
			why: 'A code graph lets the agent look up structure instead of reading whole files, which cuts tokens on big repos.',
			fix: 'Optional. Worth it when sessions regularly start by reading dozens of files.' }
	];
	const agents = Object.entries(s.agents_installed ?? {});
	const rulesFor: Record<string, boolean | undefined> = { codex: s.codex_agents_md, gemini: s.gemini_md };
	const ok = items.filter((i) => i.ok).length;
</script>

<div class="space-y-6">
	<Explain text={sectionText('setup')} />
	<div class="flex flex-wrap items-center gap-2 text-sm">
		<Badge variant={ok >= 4 ? 'default' : 'secondary'}>{ok} of {items.length} in place</Badge>
		{#each agents as [a, installed]}
			<Badge variant={installed ? 'outline' : 'secondary'}>{AGENT_LABEL[a] ?? a}: {installed ? 'found' : 'not found'}</Badge>
		{/each}
	</div>
	<div class="grid gap-3 md:grid-cols-2">
		{#each items as it}
			<Card.Root class="gap-2 px-5 py-4 {it.ok ? '' : 'border-[#d95926]/40'}">
				<div class="flex items-center gap-2 text-sm font-medium">
					{#if it.ok}<CircleCheck class="size-4 text-[#199e70]" />{:else}<CircleAlert class="size-4 text-[#d95926]" />{/if}
					{it.name}<span class="ml-auto text-xs font-normal text-muted-foreground">{it.status}</span>
				</div>
				{#if ui.long || !it.ok}<p class="text-sm text-muted-foreground">{it.why}</p>{/if}
				{#if !it.ok || ui.long}<p class="text-sm"><span class="font-medium">Fix: </span>{it.fix}</p>{/if}
			</Card.Root>
		{/each}
	</div>
	{#if agents.some(([a, i]) => i && a in rulesFor && !rulesFor[a])}
		<Card.Root class="gap-1 px-5 py-4">
			<div class="text-sm font-medium">Other agents have no rules file</div>
			<p class="text-sm text-muted-foreground">Codex reads ~/.codex/AGENTS.md and Gemini reads ~/.gemini/GEMINI.md. Copy your main rules there; `driftguard guard` writes the same drift-guard block to all of them.</p>
		</Card.Root>
	{/if}
</div>
