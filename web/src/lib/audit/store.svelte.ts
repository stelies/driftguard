// Data layer for the driftguard report. The Python side (driftguard/report.py) injects one JSON object into
// <script id="dg-data">; nothing here is hard-coded to a user. Agent filter: every view reads the filtered
// slice through `F`, and the page re-mounts the open view when the filter changes.

export type Agent = 'claude' | 'codex' | 'gemini' | 'cursor';
export type Tokens = { input?: number; output?: number; cache_read?: number; cache_write?: number };
export type Session = {
	id: string; agent: string; project: string; title: string | null; start: string; end: string; bot: boolean;
	tools: number; n: number; tokens: Tokens; tok: number; models: Record<string, number>;
	motivation: number | null; quality: number | null; issues: string[]; evidence: string | null; line: string | null;
	rage: number; switches: number; aways: number;
};
export type Prompt = { s: string; i: number; t: string; len: number; gap: number; kind: string[]; skill: boolean; txt: string };
export type Drift = { date: string; from: string; to: string; quote: string };
export type Project = {
	name: string; what_it_is: string; first: string; last: string; sessions: number; prompts: number; tokens: number;
	agents: Record<string, number>; category: string; category_reason: string; redundant_with?: string;
	status_last_seen?: string; user_confirmed?: boolean; drift?: Drift[]; judged: boolean;
};
export type Chat = { session: string; project: string; date: string; user: string; assistant_gist: string; why_notable: string; better_prompt?: string };
export type Coach = { date: string; project: string; bad: string; why: string; better: string };
export type Improve = { id: string; title: string; short: string; long: string; evidence: string[] };
export type Block = { start: string; tokens: number; turns: number };
export type Setup = {
	claude_md?: boolean; skills?: number; skill_names?: string[]; hooks?: boolean; permissions_allow?: number; mcp_servers?: number;
	graphify?: boolean; agents_installed?: Record<string, boolean>; codex_agents_md?: boolean; gemini_md?: boolean;
};
type Raw = {
	generated: string; version: string; setup: Setup; mode: { diagnostics: string; frugal: boolean; why?: string[] };
	summary: {
		counts: { transcripts: number; real: number; bot: number; prompts: number; by_agent: Record<string, number> };
		experience: { level: string; real_sessions: number; span_days: number; reasons: string[] };
		tokens: { level: string; limit_mentions: number; top10_share: number; p90_block_tokens: number; total_tokens: number; blocks: number };
		models: Record<string, number>; projects: Record<string, { sessions: number; prompts: number; tokens: number; first: string; last: string; agents: Record<string, number> }>;
		per_session: Record<string, { aways: number; rage: number; switches: number }>;
		prompts: Prompt[]; tz_offset_hours: number;
	};
	sessions: any[]; blocks: Block[];
	findings: any;
};

function load(): Raw {
	let txt = '';
	try {
		txt = document.getElementById('dg-data')?.textContent?.trim() ?? '';
		if (!txt || txt === '__DG_DATA__') {
			// dev server: `public/demo-data.json` written by scripts/make_demo_data.py (sync so imports stay simple)
			const x = new XMLHttpRequest();
			x.open('GET', '/demo-data.json', false);
			x.send();
			txt = x.status === 200 ? x.responseText : '';
		}
	} catch {
		txt = '';
	}
	if (txt) {
		try {
			return JSON.parse(txt);
		} catch (e) {
			console.error('driftguard: bad report data', e);
		}
	}
	return {
		generated: '', version: '', setup: {}, mode: { diagnostics: 'compact', frugal: false },
		summary: { counts: { transcripts: 0, real: 0, bot: 0, prompts: 0, by_agent: {} }, experience: { level: 'new', real_sessions: 0, span_days: 0, reasons: [] },
			tokens: { level: 'low', limit_mentions: 0, top10_share: 0, p90_block_tokens: 0, total_tokens: 0, blocks: 0 }, models: {}, projects: {}, per_session: {}, prompts: [], tz_offset_hours: 0 },
		sessions: [], blocks: [], findings: {}
	};
}
const raw = load();
export const META = { generated: raw.generated, version: raw.version, setup: raw.setup ?? {}, mode: raw.mode, summary: raw.summary };
export const BLOCKS: Block[] = raw.blocks ?? [];
export const EMPTY = raw.sessions.length === 0;

// ---------- findings (agent pass) ----------
const fd = raw.findings ?? {};
const fSessions = new Map<string, any>((fd.sessions ?? []).map((s: any) => [s.session, s]));
const fProjects = new Map<string, any>((fd.projects ?? []).map((p: any) => [p.name, p]));
export const FINDINGS = {
	sessions: (fd.sessions ?? []).length, projects: (fd.projects ?? []).length,
	chats: (fd.example_chats ?? []) as Chat[], patterns: (fd.patterns ?? []) as string[],
	coach: (fd.coach ?? []) as Coach[], improve: (fd.improve ?? []) as Improve[],
	answers: (fd.answers ?? {}) as Record<string, any>
};
export const HAS_FINDINGS = FINDINGS.sessions + FINDINGS.projects + FINDINGS.chats.length + FINDINGS.coach.length + FINDINGS.improve.length > 0;

// ---------- palette (validated categorical palette, dark mode, fixed slot order) ----------
export const SERIES = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];
export const CATEGORY_ORDER = [
	'useful-and-good', 'useful-but-redundant', 'done-no-updates-needed', 'stalled',
	'dopamine-build', 'moved-elsewhere', 'abandoned', 'unclear', 'unjudged'
];
export const catColor = (c: string) => (c === 'unjudged' ? '#5a5955' : (SERIES[Math.max(0, CATEGORY_ORDER.indexOf(c))] ?? SERIES[7]));
export const KINDS = ['away', 'rage', 'switch'] as const;
export const KIND_LABEL: Record<string, string> = { away: 'Away 40m+', rage: 'Frustration', switch: 'Topic switch' };
export const kindColor = (k: string) => SERIES[KINDS.indexOf(k as never)] ?? '#898781';
export const INK = { muted: '#898781', grid: '#2c2c2a', axis: '#383835', surface: '#1a1a19', text: '#f0efec', text2: '#c3c2b7' };
export const AGENT_LABEL: Record<string, string> = { claude: 'Claude Code', codex: 'Codex', gemini: 'Antigravity', cursor: 'Cursor' };
export const AGENT_COLOR: Record<string, string> = { claude: SERIES[1], codex: SERIES[0], gemini: SERIES[6], cursor: SERIES[2] };
const ACTIONS_BASE: Record<string, { label: string; verb: string }> = {
	'useful-and-good': { label: 'Keep', verb: 'Keep investing' },
	'useful-but-redundant': { label: 'Redundant', verb: 'Keep only the unique part' },
	'done-no-updates-needed': { label: 'Done', verb: 'Leave it' },
	stalled: { label: 'Stalled', verb: 'Ship or kill' },
	'dopamine-build': { label: 'Dopamine', verb: 'Kill / archive' },
	'moved-elsewhere': { label: 'Moved', verb: 'Not yours here anymore' },
	abandoned: { label: 'Abandoned', verb: 'Archive' },
	unclear: { label: 'Unclear', verb: 'Decide' },
	unjudged: { label: 'Not judged', verb: 'Run the agent pass' }
};
export const ACTIONS: Record<string, { label: string; verb: string }> = new Proxy(ACTIONS_BASE, {
	get: (t, k) => t[k as string] ?? { label: String(k), verb: '' }
});

// ---------- time ----------
export const TZ = raw.summary.tz_offset_hours ?? 0;
export const TZ_LABEL = `UTC${TZ >= 0 ? '+' : '-'}${Math.abs(TZ)}`;
export const local = (t: string) => new Date(new Date(t).getTime() + TZ * 3600e3);
export const day = (t: string) => local(t).toISOString().slice(0, 10);
export const monthOf = (t: string) => local(t).toISOString().slice(0, 7);

// ---------- normalised sessions ----------
const tokTotal = (t: Tokens) => (t.input ?? 0) + (t.output ?? 0) + (t.cache_read ?? 0) + (t.cache_write ?? 0);
const ALL_SESSIONS: Session[] = raw.sessions.map((s: any) => {
	const f = fSessions.get(s.id);
	const ps = raw.summary.per_session?.[s.id];
	return {
		id: s.id, agent: s.agent ?? 'claude', project: s.project ?? '?', title: s.title ?? f?.title ?? null, start: s.start, end: s.end ?? s.start,
		bot: !!s.bot, tools: s.tools ?? 0, n: s.n ?? 0, tokens: s.tokens ?? {}, tok: tokTotal(s.tokens ?? {}), models: s.models ?? {},
		motivation: f?.motivation ?? null, quality: f?.prompt_quality ?? null, issues: f?.prompt_issues ?? [],
		evidence: f?.motivation_evidence ?? null, line: f?.one_line ?? null,
		aways: ps?.aways ?? 0, rage: ps?.rage ?? 0, switches: ps?.switches ?? 0
	};
});
export const ALL = ALL_SESSIONS;
export const sessionById = new Map(ALL_SESSIONS.map((s) => [s.id, s]));
export const AGENTS = Object.keys(raw.summary.counts.by_agent ?? {}).filter((a) => raw.summary.counts.by_agent[a] > 0);

// Axis range shared by every time chart (not filter dependent, so axes stay put when toggling agents).
const starts = ALL_SESSIONS.map((s) => new Date(s.start).getTime()).filter((x) => !isNaN(x));
const lo = starts.length ? Math.min(...starts) : Date.now() - 30 * 864e5;
const hi = starts.length ? Math.max(...starts) : Date.now();
const pad = Math.max(864e5, (7 * 864e5 - (hi - lo)) / 2);
export const T0 = new Date(lo - Math.max(864e5, pad));
export const T1 = new Date(hi + Math.max(864e5, pad));
export const SPAN_DAYS = (T1.getTime() - T0.getTime()) / 864e5;
export const tickFmt = (d: Date) =>
	SPAN_DAYS > 75 ? d.toLocaleString('en', { month: 'short' }) : d.toLocaleString('en', { month: 'short', day: 'numeric' });
export const monthLabel = (m: string) => {
	const d = new Date(m + '-01T00:00:00Z');
	const mon = d.toLocaleString('en', { month: 'short', timeZone: 'UTC' });
	return SPAN_DAYS > 330 ? `${mon} '${m.slice(2, 4)}` : mon;
};
export const rangeLabel = `${T0.toISOString().slice(0, 10)} to ${T1.toISOString().slice(0, 10)}`;

// ---------- UI state ----------
export const ui = $state({
	section: 'overview' as string,
	long: raw.mode?.diagnostics === 'scaled',
	agents: [] as string[],
	session: null as string | null,
	project: null as string | null,
	day: null as string | null,
	tip: null as null | { x: number; y: number; title: string; body?: string; rows?: [string, string][] }
});

// ---------- filtered view ----------
function build(agents: string[]) {
	const on = agents.length ? new Set(agents) : null;
	const sessions = on ? ALL_SESSIONS.filter((s) => on.has(s.agent)) : ALL_SESSIONS;
	const human = sessions.filter((s) => !s.bot);
	const ids = new Set(human.map((s) => s.id));
	const prompts = raw.summary.prompts.filter((p) => ids.has(p.s));
	const pbs = new Map<string, Prompt[]>();
	for (const p of prompts) {
		const a = pbs.get(p.s) ?? [];
		a.push(p);
		pbs.set(p.s, a);
	}
	const by = new Map<string, Project>();
	for (const s of human) {
		const f = fProjects.get(s.project);
		let p = by.get(s.project);
		if (!p) {
			p = {
				name: s.project, what_it_is: f?.what_it_is ?? '', first: s.start, last: s.end, sessions: 0, prompts: 0, tokens: 0, agents: {},
				category: f?.category ?? 'unjudged', category_reason: f?.category_reason ?? '', redundant_with: f?.redundant_with || undefined,
				status_last_seen: f?.status_last_seen, user_confirmed: !!f?.user_confirmed, drift: f?.drift ?? [], judged: !!f
			};
			by.set(s.project, p);
		}
		p.sessions++;
		p.prompts += pbs.get(s.id)?.length ?? 0;
		p.tokens += s.tok;
		p.agents[s.agent] = (p.agents[s.agent] ?? 0) + 1;
		if (s.start < p.first) p.first = s.start;
		if (s.end > p.last) p.last = s.end;
	}
	// findings can name a project the scan does not know (e.g. a drift-only entry); keep it when no filter hides everything
	if (!on) for (const [name, f] of fProjects) if (!by.has(name) && (f.drift?.length ?? 0) > 0)
		by.set(name, { name, what_it_is: f.what_it_is ?? '', first: '', last: '', sessions: 0, prompts: 0, tokens: 0, agents: {}, category: f.category ?? 'unclear',
			category_reason: f.category_reason ?? '', redundant_with: f.redundant_with || undefined, status_last_seen: f.status_last_seen, user_confirmed: !!f.user_confirmed, drift: f.drift ?? [], judged: true });
	const projects = [...by.values()];
	const byName = new Map(projects.map((p) => [p.name, p]));
	return { sessions, human, prompts, pbs, projects, byName };
}
let cur = $derived(build(ui.agents));
export const F = {
	get sessions() { return cur.sessions; },
	get human() { return cur.human; },
	get prompts() { return cur.prompts; },
	get promptsBySession() { return cur.pbs; },
	get projects() { return cur.projects; }
};
export const filterKey = () => ui.agents.slice().sort().join(',');
export const projectOf = (s: Session) => cur.byName.get(s.project);
export const categoryOf = (s: Session) => projectOf(s)?.category ?? 'unjudged';

// ---------- sections ----------
const BASE = [
	{ id: 'overview', label: 'Overview' },
	{ id: 'motivation', label: 'Motivation timeline' },
	{ id: 'prompts', label: 'Prompt quality' },
	{ id: 'disconnect', label: 'Focus map' },
	{ id: 'three', label: '3D views' },
	{ id: 'projects', label: 'Projects: kill / keep' },
	{ id: 'drift', label: 'Drift graph' },
	{ id: 'chats', label: 'Example chats' },
	{ id: 'improve', label: 'What to improve' },
	{ id: 'tokens', label: 'Tokens' },
	{ id: 'setup', label: 'Setup health' },
	{ id: 'diagnostics', label: 'Diagnostics' }
] as const;
export const SCALED = raw.mode?.diagnostics === 'scaled';
export const FRUGAL = !!raw.mode?.frugal;
function order() {
	let ids: string[] = BASE.map((b) => b.id);
	if (SCALED) ids = ['setup', ...ids.filter((i) => i !== 'setup')];
	if (FRUGAL) {
		ids = ids.filter((i) => i !== 'tokens');
		ids.splice(1, 0, 'tokens');
	}
	return ids.map((id) => BASE.find((b) => b.id === id)!);
}
export const SECTIONS = order();

// ---------- tooltip + navigation ----------
export function showTip(e: MouseEvent, title: string, body?: string, rows?: [string, string][]) {
	ui.tip = { x: e.clientX, y: e.clientY, title, body, rows };
}
export const hideTip = () => (ui.tip = null);
export const openSession = (id: string) => {
	ui.tip = null;
	ui.session = id;
};
export const openProject = (name: string) => {
	ui.tip = null;
	ui.project = name;
};

export const mean = (a: (number | null | undefined)[]) => {
	const v = a.filter((x): x is number => typeof x === 'number');
	return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null;
};
export const short = (s: string, n = 140) => (s.length > n ? s.slice(0, n - 1) + '…' : s);
export const fmtTok = (n: number) => (n >= 1e9 ? (n / 1e9).toFixed(2) + 'B' : n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'k' : String(Math.round(n)));
export const pct = (a: number, b: number) => (b ? Math.round((100 * a) / b) : 0);
