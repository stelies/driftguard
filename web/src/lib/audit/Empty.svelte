<script lang="ts">
	import * as Card from '$lib/components/ui/card';
	import { SearchCheck } from '@lucide/svelte';
	let { title = 'Needs the agent pass', hint = 'Run /driftguard in your coding agent: it reads the prompt digests, scores sessions, judges projects and writes findings.json. Then rebuild this report with `driftguard report`.' }: { title?: string; hint?: string } = $props();
</script>

<Card.Root class="items-center gap-2 border-dashed px-6 py-10 text-center">
	<SearchCheck class="size-8 text-muted-foreground" />
	<div class="text-sm font-medium">{title}</div>
	<p class="max-w-xl text-sm text-muted-foreground">{hint}</p>
</Card.Root>
