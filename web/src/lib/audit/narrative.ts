// Report text generated from the data. Every sentence carries real numbers; nothing is written for a specific user.
import { F, META, HAS_FINDINGS, FINDINGS, mean, monthOf, monthLabel, pct, fmtTok, TZ_LABEL, ACTIONS, SCALED } from './store.svelte';

export type Text = { short: string; long: string };

export function stats() {
	const hs = F.human, ps = F.prompts, pbs = F.promptsBySession;
	const disc = ps.filter((p) => p.kind.length);
	const withDis = hs.filter((s) => (pbs.get(s.id) ?? []).some((p) => p.kind.length));
	const firsts = withDis.map((s) => (pbs.get(s.id) ?? []).find((p) => p.kind.length)!.i + 1).sort((a, b) => a - b);
	const rate = (i: number) => {
		const at = ps.filter((p) => p.i === i);
		return { n: at.length, r: at.length ? at.filter((p) => p.kind.length).length / at.length : 0 };
	};
	let cliff: { at: number; from: number; to: number } | null = null;
	for (let i = 1; i < 10; i++) {
		const a = rate(i - 1), b = rate(i);
		if (a.n >= 5 && b.n >= 5 && b.r - a.r > (cliff ? cliff.to - cliff.from : 0.04)) cliff = { at: i + 1, from: a.r, to: b.r };
	}
	const months: Record<string, number> = {};
	for (const s of hs) months[monthOf(s.start)] = (months[monthOf(s.start)] ?? 0) + 1;
	const topMonth = Object.entries(months).sort((a, b) => b[1] - a[1])[0];
	const byMonthQ: [string, number][] = Object.keys(months).sort().map((m) => [m, mean(hs.filter((s) => monthOf(s.start) === m).map((s) => s.quality)) as number] as [string, number]).filter(([, q]) => q != null);
	const qTrend = byMonthQ.length >= 2 ? { a: byMonthQ[0], b: byMonthQ.at(-1)! } : null;
	const tok = hs.reduce((a, s) => a + s.tok, 0);
	const cache = hs.reduce((a, s) => a + (s.tokens.cache_read ?? 0), 0);
	const top = hs.slice().sort((a, b) => b.tok - a.tok).slice(0, 10);
	return {
		real: hs.length, bot: F.sessions.length - hs.length, prompts: ps.length, disc: disc.length, withDis: withDis.length,
		medFirst: firsts.length ? firsts[Math.floor(firsts.length / 2)] : null, cliff, topMonth, qTrend, tok, cachePct: pct(cache, tok),
		top10Pct: pct(top.reduce((a, s) => a + s.tok, 0), tok), months: Object.keys(months).sort(),
		away: ps.filter((p) => p.kind.includes('away')).length, rage: ps.filter((p) => p.kind.includes('rage')).length, sw: ps.filter((p) => p.kind.includes('switch')).length
	};
}

const NEED = 'Run the agent pass (/driftguard in your agent) to add verdicts, scores and coaching. Every metric view below already works without it.';

export function headline(): Text {
	const s = stats();
	if (!s.real) return { short: 'No sessions found for this selection.', long: 'Run `driftguard scan` after using an agent, or switch the agent filter in the sidebar.' };
	const parts = [`${s.real} real sessions and ${s.prompts} prompts`];
	if (s.withDis) parts.push(`${pct(s.withDis, s.real)}% of sessions had at least one focus break`);
	if (s.topMonth) parts.push(`${monthLabel(s.topMonth[0])} was the busiest month (${s.topMonth[1]} sessions, ${pct(s.topMonth[1], s.real)}%)`);
	if (s.qTrend) {
		const [a, b] = [s.qTrend.a[1], s.qTrend.b[1]];
		const range = `between ${monthLabel(s.qTrend.a[0])} and ${monthLabel(s.qTrend.b[0])}`;
		parts.push(Math.abs(b - a) < 0.15 ? `Prompt quality held steady at ${b.toFixed(1)} of 5 ${range}` : `Prompt quality ${b > a ? 'rose' : 'fell'} from ${a.toFixed(1)} to ${b.toFixed(1)} of 5 ${range}`);
	}
	const long = [
		`This report reads ${F.sessions.length} transcripts. ${s.bot} were machine-generated (summarizers, title jobs, test harnesses) and are excluded, which leaves ${s.real} real sessions with ${s.prompts} typed prompts.`,
		s.disc ? `${s.disc} prompts (${pct(s.disc, s.prompts)}%) were a focus break: ${s.away} after a 40+ minute absence, ${s.sw} abrupt topic switches, ${s.rage} frustration spikes. The median session had its first break at prompt #${s.medFirst}.` : 'No focus breaks were detected.',
		s.cliff ? `The break rate climbs from ${Math.round(s.cliff.from * 100)}% at prompt #${s.cliff.at - 1} to ${Math.round(s.cliff.to * 100)}% at prompt #${s.cliff.at}: that is where sessions start to drift.` : '',
		s.tok ? `Token spend was ${fmtTok(s.tok)} in total, ${s.cachePct}% of it cache reads, and the ten costliest sessions account for ${s.top10Pct}% (see Tokens).` : '',
		HAS_FINDINGS ? '' : NEED
	].filter(Boolean).join('\n\n');
	return { short: parts.join('. ') + '.', long };
}

export function sectionText(id: string): Text {
	const s = stats();
	switch (id) {
		case 'motivation':
			return HAS_FINDINGS
				? { short: 'Daily average of the agent-scored motivation (1-5). Drag across the chart to select a period, click a dot for that day.',
					long: `Each point is one day: the mean motivation score of that day's real sessions, as judged by the agent pass from your prompts (praise, long specs and concrete next steps score high; sarcasm, caps and "forget it" score low). Orange dots are days with frustration prompts.\n\nLook for what the high days have in common (usually an outside deadline) and what precedes the low days. Dashed lines mark drift dates found in your projects, or your worst frustration days.` }
				: { short: 'Motivation scores come from the agent pass, which has not run yet. Frustration days from the scan are marked below.',
					long: `${NEED}\n\nUntil then this view shows the deterministic part: how many sessions you had per day, and which days contained frustration prompts (orange).` };
		case 'prompts':
			return { short: `${s.prompts} prompts plotted by length over time; coloured dots are focus breaks.`,
				long: `Every dot is one prompt you typed, placed by date (x) and length in characters (y, log scale). Very long dots are pasted specs or logs. Coloured dots are focus breaks: away (${s.away}), topic switch (${s.sw}), frustration (${s.rage}).\n\nA wall of short coloured dots in one period usually means rapid-fire fixing without a spec. ${HAS_FINDINGS ? 'Coaching cards below rewrite your weakest prompts; click a card to flip it.' : NEED}` };
		case 'disconnect':
			return { short: s.cliff ? `Focus breaks jump at prompt #${s.cliff.at}; ${pct(s.withDis, s.real)}% of sessions had one.` : `${pct(s.withDis, s.real)}% of sessions had at least one focus break.`,
				long: `A focus break is detected without any AI: **away** = 40+ minutes since your previous prompt, **topic switch** = a long prompt that shares almost no words with the last three, **frustration** = rage words, caps or "??" in a short prompt.\n\nThe focus-decay chart shows what share of prompts at each position in a session are breaks. The heatmap shows ${TZ_LABEL} hour by weekday; orange outlines mark hours where 40%+ of prompts are breaks. The strips at the bottom show every session as a timeline.` };
		case 'three':
			return { short: 'The same data in 3D. Drag to rotate, wheel to zoom, click a point or tower to open it.',
				long: `**Sessions cloud**: date, motivation and prompt quality as axes${HAS_FINDINGS ? '' : ' (needs the agent pass for scores, so it is empty for now)'}. **Brain terrain**: hour of day by weekday, height = prompts, colour = break rate. **Project towers**: sessions per project per month, colour = verdict.` };
		case 'projects':
			return HAS_FINDINGS
				? { short: 'Every project with a keep / fix / kill verdict and the evidence behind it.', long: `Verdicts come from the agent pass reading what each project is and how it was used. Columns group them into actions. Click a card for the drift history and sessions. The timeline shows when each project was alive; a long thin bar with many ticks is a project you keep returning to.` }
				: { short: `${F.projects.length} projects found. Verdicts need the agent pass.`, long: `${NEED}\n\nFor now this lists every project (working-directory name) with its session count and activity span. Projects with one or two sessions that never came back are the likeliest candidates to archive.` };
		case 'drift':
			return { short: 'Where a project turned into something else, as quoted from your own prompts.',
				long: `Each large node is a project; each small node is what it drifted into. Click an edge to read the quote. Drag nodes to untangle, double-click a project to open it.\n\n${HAS_FINDINGS ? '' : NEED}` };
		case 'chats':
			return { short: 'Verbatim exchanges the agent pass flagged as instructive.', long: `Each pair is what you wrote and the gist of the answer, with why it matters and a better prompt where there is one.\n\n${HAS_FINDINGS ? '' : NEED}` };
		case 'improve':
			return { short: 'A short, ordered fix list. Tick items off; progress is kept in this browser.', long: `The list is generated from the patterns in your own sessions, strongest evidence first. Evidence chips link to the views that show the data.\n\n${HAS_FINDINGS ? '' : NEED}` };
		case 'tokens':
			return { short: `${fmtTok(s.tok)} tokens, ${s.cachePct}% cache reads; the top 10 sessions are ${s.top10Pct}% of the spend.`,
				long: `Tokens are summed per session (input + output + cache reads + cache writes) and attributed to the day the session started. Cache reads are cheap re-reads of earlier context, so a high share is normal for long sessions; what hurts is the number of long sessions.\n\nThe 5-hour blocks chart groups assistant turns into the rolling windows most plans limit on. The dashed line is your 90th-percentile block: blocks above it are the ones that hit limits. Blocks cover all agents even when the agent filter is on.` };
		case 'setup':
			return { short: 'What your agents already have configured, and the cheapest fix for each gap.', long: `Rules files, skills, hooks and MCP servers are what turn a generic agent into one that knows your projects. Items below are checked on this machine at scan time; each has a plain-language fix.${SCALED ? '\n\nYou are early in your history or have little configured, so this section comes first and explanations are on by default.' : ''}` };
		default:
			return { short: 'How every number in this report was computed, plus the raw session table.', long: `Real sessions have at least one typed prompt and are not auto-generated. Heuristics are deterministic and use no AI: see the list below. Scores for motivation and quality come from the agent pass (${HAS_FINDINGS ? 'present' : 'not run yet'}).` };
	}
}

export const coachEmpty = NEED;
export const catLabel = (c: string) => ACTIONS[c]?.label ?? c;
export { FINDINGS, META };
