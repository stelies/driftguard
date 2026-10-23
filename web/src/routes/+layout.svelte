<script lang="ts">
	import '../app.css';
	import * as Tooltip from '$lib/components/ui/tooltip';

	let { children } = $props();
</script>

<svelte:head><title>driftguard report</title></svelte:head>
<Tooltip.Provider delayDuration={150}>
	{@render children?.()}
</Tooltip.Provider>
