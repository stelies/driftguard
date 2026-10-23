<script lang="ts">
	import { ui } from './store.svelte';
	import type { Text } from './narrative';
	let { text }: { text: Text } = $props();
	let open = $state<boolean | null>(null);
	const isLong = $derived(open ?? ui.long);
	const paras = (s: string) => s.split(/\n\n+/);
	const md = (s: string) =>
		s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n- /g, '<br>• ');
</script>

<div class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
	<p class="text-foreground">{text.short}</p>
	{#if isLong}
		{#each paras(text.long) as p}
			<p class="mt-3">{@html md(p)}</p>
		{/each}
	{/if}
	<button class="mt-2 text-xs font-medium text-primary underline-offset-4 hover:underline" onclick={() => (open = !isLong)}>
		{isLong ? 'Short version' : 'Long explanation'}
	</button>
</div>
