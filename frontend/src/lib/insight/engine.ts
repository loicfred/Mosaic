/**
 * Valora Insight answers come from the LLM endpoint (POST /insight/ask, see
 * backend/app/services/assistant_service.py). This file holds the shared answer
 * types and the offline fallback used when that endpoint is unavailable: a
 * question router that matches a fixed set of intents and phrases figures the
 * Valora API already computed, refusing anything outside those intents.
 */
import { GAIN_KINDS, RISK_KINDS } from '@/lib/findings'
import { date, monthLabel, murCompact, pct, pp } from '@/lib/format'
import type { LedgerHealth, MonthRow, Opportunity, Overview } from '@/lib/types'

export type DataKindName = 'actual' | 'projected' | 'predicted' | 'simulated'

export interface Fact {
  label: string
  value: string
  tone?: 'good' | 'bad' | 'warn'
}

export type Visual =
  | { type: 'spark'; values: number[]; label: string; color?: string; caption?: string }
  | { type: 'bars'; rows: { label: string; value: number; display: string }[]; label: string; color?: string }

export interface Source {
  /** What the figure is, e.g. "Cash balance". */
  label: string
  /** Where it comes from, e.g. "Ledger, actual, data to 22 Sep 2026". */
  detail: string
  /** App route that shows the same figure. */
  to?: string
}

export interface Answer {
  /** 'busy': the AI hit its rate limit; the question can be retried after `retryAfter` seconds. */
  status: 'answer' | 'refusal' | 'empty' | 'busy'
  intent: string
  headline: string
  body?: string
  facts: Fact[]
  visual?: Visual
  kind?: DataKindName
  sources: Source[]
  followUps: string[]
  /** Who answered: the LLM, or the local rules when the LLM is unavailable. */
  via?: 'llm' | 'rules'
  /** LLM model id, shown on the answer. */
  model?: string
  /** Total tokens the LLM call used, shown next to the model. */
  tokens?: number
  /** True when the rules answered because the AI could not be reached (not by the user's choice). */
  fallback?: boolean
  retryAfter?: number
}

/** The subset of GET /insights used here. */
export interface InsightsData {
  as_of: string
  monthly: MonthRow[]
  comparison_90d?: {
    current: Record<string, number>
    previous: Record<string, number>
    change_pct: Record<string, number | null>
    current_period: [string, string]
    previous_period: [string, string]
  }
  expense_categories?: { category: string; amount: number; share_pct: number; change_pct: number | null }[]
  product_lines?: { line: string; revenue: number; share_pct: number; change_pct: number | null }[]
  customer_concentration?: Concentration
  supplier_concentration?: Concentration
  recurring?: {
    name: string
    category: string
    monthly_run_rate: number
    active: boolean
    is_new: boolean
  }[]
  collections?: {
    has_invoices: boolean
    collection_days_recent: number | null
    collection_days_prior: number | null
    open_receivables: number
    overdue_receivables: number
    standard_terms_days: number
    by_customer: { customer: string; open_amount: number; overdue_amount: number; avg_days_to_pay_recent: number | null }[]
  }
}

interface Concentration {
  days: number
  total: number
  top: { name: string; amount: number; share_pct: number }[]
  top_share_pct: number
  top3_share_pct: number
  unidentified_amount: number
  unidentified_label: string
}

export interface InsightContext {
  businessName: string
  overview?: Overview
  opportunities?: Opportunity[]
  insights?: InsightsData
  health?: LedgerHealth
}

/** Optional pointer to what the user was looking at when they asked. */
export type AskContext = { type: 'finding'; id: string } | { type: 'chart'; chart: 'cash' | 'monthly' | 'kpis' | 'worth' }

export const SUGGESTED: string[] = [
  'How much cash do we have?',
  'Will cash fall below the safety buffer?',
  'What is the biggest opportunity?',
  'Where does most of the money go?',
  'Which customers owe us the most?',
  'How reliable is the data?',
]

/** Suggested questions for the page the user is on; every one is answerable from loaded data. */
const BY_PAGE: [string, string[]][] = [
  [
    '/insights',
    ['How did revenue change recently?', 'Why did gross margin change?', 'Where does most of the money go?', 'What was our best month?'],
  ],
  [
    '/transactions',
    [
      'Where does most of the money go?',
      'What are our recurring costs?',
      'How dependent are we on one supplier?',
      'Which customers owe us the most?',
    ],
  ],
  [
    '/opportunities',
    ['What is the biggest opportunity?', 'What is the biggest risk?', 'What should I look at first?', 'Did the actions work?'],
  ],
  ['/scenarios', ['Will cash fall below the safety buffer?', 'What is the 30-day cash pressure risk?', 'How much cash do we have?']],
  ['/data-health', ['How reliable is the data?', 'How much cash do we have?']],
  [
    '/',
    [
      'How much cash do we have?',
      'Will cash fall below the safety buffer?',
      'What should I look at first?',
      'How did revenue change recently?',
    ],
  ],
]

export function suggestionsFor(pathname: string): string[] {
  return BY_PAGE.find(([path]) => (path === '/' ? pathname === '/' : pathname.startsWith(path)))?.[1] ?? SUGGESTED
}

/* ---------- intent matching ---------- */

type Intent =
  | 'cash_now'
  | 'cash_outlook'
  | 'cash_pressure'
  | 'revenue'
  | 'expenses'
  | 'margin'
  | 'best_month'
  | 'collections'
  | 'customers'
  | 'suppliers'
  | 'recurring'
  | 'product_lines'
  | 'opportunity'
  | 'risk'
  | 'priorities'
  | 'outcomes'
  | 'data_health'
  | 'monthly_story'

const RULES: { intent: Intent; any: RegExp[]; boost?: RegExp[] }[] = [
  {
    intent: 'cash_outlook',
    any: [
      /\bbuffer\b/,
      /run(ning)? out/,
      /\brunway\b/,
      /\bprojection|projected\b/,
      /\blowest\b/,
      /next 90/,
      /fall below|drop below|go below|below the/,
    ],
    boost: [/\bcash\b/],
  },
  {
    intent: 'cash_pressure',
    any: [/\bpressure\b/, /\bprobab/, /\bchance\b/, /\blikely\b/, /\bmodel\b/, /next 30/],
    boost: [/\bcash\b/, /\brisk\b/],
  },
  {
    intent: 'cash_now',
    any: [/\bcash\b/, /\bbalance\b/, /in the bank/, /how much money/],
    boost: [/\bnow\b|\btoday\b|\bcurrent/, /how much/],
  },
  {
    intent: 'revenue',
    any: [/\brevenue\b/, /\bsales\b/, /\bincome\b/, /\bturnover\b/, /\bearn/],
    boost: [/\bchange|trend|grow|fell|drop|up|down/],
  },
  { intent: 'recurring', any: [/\brecurring\b/, /\bsubscription/, /\bmonthly bills?\b/, /\bfixed costs?\b/, /\bpayroll\b/, /\brent\b/] },
  {
    intent: 'expenses',
    any: [/\bexpens/, /\bspend/, /\bcosts?\b/, /money go/, /\bcategor/, /\boutflow/],
    boost: [/\bbiggest|largest|most|where\b/],
  },
  { intent: 'margin', any: [/\bmargin\b/, /\bprofit/, /gross/] },
  {
    intent: 'best_month',
    any: [
      /\bbest month\b/,
      /\bworst month\b/,
      /which month/,
      /\bmonth\b.*\b(highest|lowest|best|worst)\b/,
      /\b(highest|lowest)\b.*\bmonth/,
    ],
  },
  {
    intent: 'collections',
    any: [/\bowe\b/, /\bowes\b/, /\boverdue\b/, /\breceivabl/, /\binvoice/, /\bpay(ing)? (us )?(late|slow)/, /\bcollect/, /days to pay/],
    boost: [/\bcustomer/],
  },
  { intent: 'customers', any: [/\bcustomers?\b/, /\bclients?\b/], boost: [/\bdepend|reliant|concentrat|top|biggest|largest\b/] },
  {
    intent: 'suppliers',
    any: [/\bsuppliers?\b/, /\bvendors?\b/, /\bwholesal/],
    boost: [/\bdepend|reliant|concentrat|top|biggest|largest\b/],
  },
  { intent: 'product_lines', any: [/\bproduct/, /\blines?\b/, /\bwhat sells\b/, /\bbest.?sell/] },
  { intent: 'opportunity', any: [/\bopportunit/, /\bsav(e|ing)/, /\bgain\b/, /\bupside\b/, /\bimprove\b/] },
  { intent: 'risk', any: [/\brisks?\b/, /\bthreat/, /\bexposure\b/, /\bworr/, /\bdanger/] },
  {
    intent: 'priorities',
    any: [
      /\bfirst\b/,
      /\bpriorit/,
      /\bfocus\b/,
      /\battention\b/,
      /\bwhat should (i|we) (look|do|check|start)/,
      /\bwhat needs\b/,
      /\burgent\b/,
      /\bthis week\b/,
    ],
  },
  {
    intent: 'outcomes',
    any: [/\bdid (it|they|the action|the actions)\b/, /\bwork(ed)?\b/, /\boutcome/, /\bresults?\b/, /\bmeasured\b/, /\bachiev/],
  },
  {
    intent: 'data_health',
    any: [
      /\bdata\b.*\b(quality|health|reliable|trust|clean|messy|issues?|accurate)\b/,
      /\b(quality|reliable|trust|accurate)\b.*\bdata\b/,
      /\bdata health\b/,
      /\bduplicat/,
      /\buncategori[sz]ed\b/,
      /\bmissing\b/,
    ],
  },
  {
    intent: 'monthly_story',
    any: [
      /\bmonth by month\b/,
      /\beach month\b/,
      /\bmonthly\b/,
      /\blast (12|twelve) months\b/,
      /\bmaking (a )?(profit|money|a loss)\b/,
      /\bnet cash( flow)?\b/,
    ],
  },
]

const FORECAST =
  /\b(forecast|predict(ion)?s?|next (year|quarter)|in 20\d\d|will (we|revenue|sales|profit|margin|expenses|costs|customers)|future (revenue|sales|profit)|by (the )?end of (the )?year|grow next)\b/
const EXTERNAL =
  /\b(competitors?|the market|market share|industry|economy|inflation|exchange rates?|interest rates?|stock market|shares? price|crypto|bitcoin|weather|news|government|tax law|legal advice|lawyer|benchmark|other businesses|average (business|company))\b/
const DECISION =
  /\b(should (i|we) (fire|hire|sell|buy|invest|borrow|close|open|lay off|cut staff|take (a|the) loan|expand)|decide for (me|us)|make the decision|approve (it|this) for me|do it for me)\b/
const OFF_TOPIC = /\b(poem|joke|story|recipe|song|translate|write (me )?(an? )?(email|essay|letter)|who are you|tell me about yourself)\b/

function normalise(q: string) {
  return q
    .toLowerCase()
    .replace(/[’']/g, "'")
    .replace(/[^a-z0-9%' ]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

export function matchIntent(question: string): Intent | null {
  const q = normalise(question)
  let best: { intent: Intent; score: number } | null = null
  for (const r of RULES) {
    const hits = r.any.filter((re) => re.test(q)).length
    if (!hits) continue
    const score = hits * 2 + (r.boost?.filter((re) => re.test(q)).length ?? 0)
    if (!best || score > best.score) best = { intent: r.intent, score }
  }
  return best?.intent ?? null
}

/* ---------- refusals ---------- */

const SCOPE = 'I can only answer questions using the business data available in Valora.'

function refusal(intent: string, headline: string, body: string, followUps = SUGGESTED.slice(0, 3)): Answer {
  return { status: 'refusal', intent, headline, body, facts: [], sources: [], followUps }
}

export function classifyOutOfScope(question: string, matched: Intent | null): Answer | null {
  const q = normalise(question)
  if (OFF_TOPIC.test(q))
    return refusal(
      'off_topic',
      SCOPE,
      'Valora Insight reads your ledger, findings and data checks. It does not write text or hold a general conversation.',
    )
  if (DECISION.test(q))
    return refusal(
      'decision',
      'Valora does not make business decisions for you.',
      'I can show the figures behind a decision: cash, costs, findings and their evidence. You can also test a change in the Scenario Lab before acting.',
      ['What is the biggest risk?', 'How much cash do we have?', 'What should I look at first?'],
    )
  if (EXTERNAL.test(q))
    return refusal(
      'external',
      SCOPE,
      'I do not have market, industry, economic or competitor data. Every answer here comes from your own recorded transactions and invoices.',
    )
  const cashTopic = matched === 'cash_outlook' || matched === 'cash_pressure' || matched === 'cash_now'
  if (FORECAST.test(q) && !cashTopic)
    return refusal(
      'forecast',
      "I don't have forecasting data for that in the current Valora dataset.",
      'Valora projects cash for the next 90 days at current run-rates, and a model estimates the chance of cash pressure in the next 30 days. It does not forecast revenue, profit or anything further ahead.',
      ['Will cash fall below the safety buffer?', 'What is the 30-day cash pressure risk?', 'How did revenue change recently?'],
    )
  if (!matched)
    return refusal(
      'unknown',
      SCOPE,
      'Try asking about cash, revenue, costs, customers, suppliers, findings or data quality.',
      SUGGESTED.slice(0, 4),
    )
  return null
}

/* ---------- answers ---------- */

const complete = (m: MonthRow[]) => m.filter((x) => !x.partial)

function src(label: string, kind: string, asOf: string | undefined, to: string): Source {
  return { label, detail: `${kind}${asOf ? `, data to ${date(asOf)}` : ''}`, to }
}

function needs(what: string, route: string): Answer {
  return {
    status: 'empty',
    intent: 'loading',
    headline: `The ${what} is not available right now.`,
    body: 'It may still be loading, or your role may not include it. Try again in a moment.',
    facts: [],
    sources: [{ label: what, detail: 'Not loaded', to: route }],
    followUps: SUGGESTED.slice(0, 3),
  }
}

const range = (o: Opportunity) =>
  o.impact_low === null || o.impact_high === null ? 'not sized' : `${murCompact(o.impact_low)}–${murCompact(o.impact_high)} a year`

function findingAnswer(o: Opportunity, intent: string, headlinePrefix?: string): Answer {
  const ev = o.evidence.slice(0, 3).map((e) => ({ label: e.label, value: e.display }))
  return {
    status: 'answer',
    intent,
    headline: `${headlinePrefix ? `${headlinePrefix}: ` : ''}${o.title}`,
    body: `${o.summary} ${o.why_it_matters}`.trim(),
    facts: [
      { label: o.kind === 'risk' ? 'Money exposed' : 'Estimated value', value: range(o), tone: o.kind === 'risk' ? 'bad' : 'good' },
      ...ev,
      { label: 'Engine confidence', value: `${Math.round(o.confidence * 100)}%` },
    ],
    sources: [
      {
        label: 'Finding',
        detail: `Opportunity engine (${o.detector.replace(/_/g, ' ')}), data to ${date(o.data_as_of)}`,
        to: `/opportunities?open=${o.id}`,
      },
    ],
    followUps: ['What should I look at first?', o.kind === 'risk' ? 'What is the biggest opportunity?' : 'What is the biggest risk?'],
  }
}

function answerFor(intent: Intent, c: InsightContext): Answer {
  const ov = c.overview
  const ins = c.insights
  const opps = (c.opportunities ?? []).filter((o) => o.is_active && ['new', 'reviewed', 'planned'].includes(o.status))
  const asOf = ov?.as_of ?? ins?.as_of

  switch (intent) {
    case 'cash_now': {
      if (!ov) return needs('cash overview', '/')
      const change = ov.cash.balance - ov.cash.balance_30d_ago
      const last90 = ov.cash_series.slice(-90).map((d) => d.cash)
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `Cash is ${murCompact(ov.cash.balance)} as of ${date(ov.as_of)}.`,
        body: `That covers about ${ov.cash.buffer_days.toFixed(0)} days of outflows; Valora's safety buffer is 14 days.`,
        facts: [
          { label: 'Cash today', value: murCompact(ov.cash.balance) },
          { label: 'Change in 30 days', value: murCompact(change, true), tone: change < 0 ? 'bad' : 'good' },
          {
            label: 'Days of outflows covered',
            value: `${ov.cash.buffer_days.toFixed(0)} days`,
            tone: ov.cash.buffer_days < 14 ? 'bad' : ov.cash.buffer_days < 21 ? 'warn' : undefined,
          },
        ],
        visual: { type: 'spark', values: last90, label: 'Cash balance, last 90 days', caption: 'End-of-day cash, last 90 days' },
        sources: [src('Cash balance', 'Ledger, actual', asOf, '/')],
        followUps: ['Will cash fall below the safety buffer?', 'What is the 30-day cash pressure risk?'],
      }
    }
    case 'cash_outlook': {
      if (!ov) return needs('cash projection', '/')
      const p = ov.projection
      if (!ov.projection_series.length)
        return {
          status: 'empty',
          intent,
          headline: 'There is not enough history to project cash yet.',
          facts: [],
          sources: [src('Cash projection', 'Deterministic projection', asOf, '/')],
          followUps: ['How much cash do we have?'],
        }
      const below = p.first_date_below_buffer
      return {
        status: 'answer',
        intent,
        kind: 'projected',
        headline: below
          ? `Yes. At current run-rates cash is projected to fall below the buffer on ${date(below)}.`
          : 'No. At current run-rates cash stays above the 14-day buffer for the next 90 days.',
        body: 'This is a deterministic projection from recent inflows and outflows, not a recorded value and not a prediction of revenue.',
        facts: [
          { label: 'Lowest point', value: `${murCompact(p.lowest_cash)} on ${date(p.lowest_cash_date)}`, tone: below ? 'bad' : undefined },
          { label: 'Safety buffer', value: murCompact(p.buffer_threshold) },
          { label: 'Days below buffer', value: `${p.days_below_buffer} of 90`, tone: p.days_below_buffer ? 'bad' : 'good' },
          { label: 'Cash in 90 days', value: murCompact(p.cash_day_90) },
        ],
        visual: {
          type: 'spark',
          values: ov.projection_series.map((d) => d.cash),
          label: 'Projected cash, next 90 days',
          color: 'var(--color-projected)',
          caption: 'Projected end-of-day cash, next 90 days',
        },
        sources: [src('90-day cash projection', 'Deterministic projection from current run-rates', asOf, '/')],
        followUps: ['What is the 30-day cash pressure risk?', 'What should I look at first?'],
      }
    }
    case 'cash_pressure': {
      if (!ov) return needs('cash pressure estimate', '/')
      const pr = ov.prediction
      if (pr.probability === null)
        return {
          status: 'empty',
          intent,
          kind: 'predicted',
          headline: 'The cash pressure model has no estimate for this business yet.',
          body: pr.reason,
          facts: [],
          sources: [src('Cash pressure model', 'Locally trained model', asOf, '/settings?tab=models')],
          followUps: ['Will cash fall below the safety buffer?'],
        }
      const drivers = (pr.top_drivers ?? []).slice(0, 3)
      return {
        status: 'answer',
        intent,
        kind: 'predicted',
        headline: `The model puts the chance of cash pressure in the next 30 days at ${Math.round(pr.probability * 100)}% (${pr.band.toLowerCase()} risk).`,
        body: 'Cash pressure means cash falling below 14 days of committed outflows. This is a model estimate with a probability, not a certainty.',
        facts: drivers.map((d) => ({ label: d.label, value: d.display })),
        visual: drivers.length
          ? {
              type: 'bars',
              label: 'What pushes the estimate up',
              rows: drivers.map((d) => ({ label: d.label, value: d.contribution, display: d.display })),
              color: 'var(--color-ink-2)',
            }
          : undefined,
        sources: [src('Cash pressure model', `Locally trained model ${pr.model_version ?? ''}`.trim(), asOf, '/settings?tab=models')],
        followUps: ['Will cash fall below the safety buffer?', 'How much cash do we have?'],
      }
    }
    case 'revenue': {
      if (!ov) return needs('revenue figures', '/insights')
      const k = ov.kpis_90d
      const full = complete(ov.monthly)
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline:
          k.revenue_change_pct === null
            ? `Revenue was ${murCompact(k.revenue)} over the last three months.`
            : `Revenue was ${murCompact(k.revenue)} over the last three months, ${pct(k.revenue_change_pct)} on the three months before.`,
        facts: [
          { label: 'Last three months', value: murCompact(k.revenue) },
          { label: 'Change', value: pct(k.revenue_change_pct), tone: (k.revenue_change_pct ?? 0) < 0 ? 'bad' : 'good' },
          ...(full.length
            ? [
                {
                  label: `Latest full month (${monthLabel(full[full.length - 1].month)})`,
                  value: murCompact(full[full.length - 1].revenue),
                },
              ]
            : []),
        ],
        visual:
          full.length > 1
            ? {
                type: 'spark',
                values: full.map((m) => m.revenue),
                label: 'Monthly revenue',
                caption: `Monthly revenue, ${full.length} full months`,
              }
            : undefined,
        sources: [src('Revenue', 'Ledger, actual', asOf, '/insights')],
        followUps: ['Why did gross margin change?', 'What was our best month?'],
      }
    }
    case 'expenses': {
      if (!ins) return needs('expense breakdown', '/insights')
      const cats = (ins.expense_categories ?? []).slice(0, 5)
      if (!cats.length) return noData(intent)
      const top = cats[0]
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `${top.category} is the biggest cost: ${murCompact(top.amount)}, ${top.share_pct.toFixed(0)}% of spending in the last three months.`,
        body: top.change_pct !== null ? `That is ${pct(top.change_pct)} on the three months before.` : undefined,
        facts: [],
        visual: {
          type: 'bars',
          label: 'Spending by category, last three months',
          rows: cats.map((x) => ({ label: x.category, value: x.amount, display: murCompact(x.amount) })),
          color: 'var(--color-expense)',
        },
        sources: [src('Expense categories', 'Ledger, actual, last three months', asOf, '/insights')],
        followUps: ['What are our recurring costs?', 'How dependent are we on one supplier?'],
      }
    }
    case 'margin': {
      if (!ov) return needs('margin figures', '/insights')
      const k = ov.kpis_90d
      const ch = ins?.comparison_90d?.change_pct
      const cogs = ch?.cost_of_goods ?? null
      const rev = ch?.revenue ?? k.revenue_change_pct
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `Gross margin is ${k.gross_margin_pct.toFixed(1)}%, ${pp(k.gross_margin_change_pp)} on the previous three months.`,
        body:
          cogs !== null && rev !== null
            ? `Over the same period supplier costs (cost of goods) changed ${pct(cogs)} while revenue changed ${pct(rev)}. Gross margin is revenue minus cost of goods, so these two figures move it.`
            : undefined,
        facts: [
          { label: 'Gross margin', value: `${k.gross_margin_pct.toFixed(1)}%` },
          { label: 'Change', value: pp(k.gross_margin_change_pp), tone: k.gross_margin_change_pp < 0 ? 'bad' : 'good' },
          ...(cogs !== null ? [{ label: 'Cost of goods', value: pct(cogs), tone: cogs > (rev ?? 0) ? ('bad' as const) : undefined }] : []),
          ...(rev !== null ? [{ label: 'Revenue', value: pct(rev) }] : []),
        ],
        visual:
          complete(ov.monthly).length > 1
            ? {
                type: 'spark',
                values: complete(ov.monthly).map((m) => m.gross_margin_pct),
                label: 'Monthly gross margin',
                caption: 'Gross margin by full month',
              }
            : undefined,
        sources: [src('Gross margin', 'Ledger, actual', asOf, '/insights')],
        followUps: ['Where does most of the money go?', 'What is the biggest risk?'],
      }
    }
    case 'best_month': {
      const months = complete(ins?.monthly ?? ov?.monthly ?? [])
      if (!months.length) return noData(intent)
      const best = months.reduce((a, b) => (b.revenue > a.revenue ? b : a))
      const worst = months.reduce((a, b) => (b.revenue < a.revenue ? b : a))
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `${monthLabel(best.month)} had the highest revenue of the last ${months.length} full months: ${murCompact(best.revenue)}.`,
        body: `The lowest was ${monthLabel(worst.month)} at ${murCompact(worst.revenue)}.`,
        facts: [
          { label: `Best (${monthLabel(best.month)})`, value: murCompact(best.revenue), tone: 'good' },
          { label: `Lowest (${monthLabel(worst.month)})`, value: murCompact(worst.revenue) },
        ],
        visual: {
          type: 'spark',
          values: months.map((m) => m.revenue),
          label: 'Monthly revenue',
          caption: `Revenue, ${monthLabel(months[0].month)} to ${monthLabel(months[months.length - 1].month)}`,
        },
        sources: [src('Monthly revenue', 'Ledger, actual', asOf, '/insights')],
        followUps: ['How did revenue change recently?', 'Why did gross margin change?'],
      }
    }
    case 'collections': {
      if (!ins) return needs('receivables data', '/insights')
      const col = ins.collections
      if (!col?.has_invoices) return noData(intent, 'No invoices are recorded for this business, so there is nothing owed to report.')
      const owing = [...col.by_customer]
        .filter((b) => b.open_amount > 0)
        .sort((a, b) => b.open_amount - a.open_amount)
        .slice(0, 4)
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `Customers owe ${murCompact(col.open_receivables)} in open invoices; ${murCompact(col.overdue_receivables)} of it is overdue.`,
        body:
          col.collection_days_recent !== null && col.collection_days_prior !== null
            ? `Customers now take ${col.collection_days_recent.toFixed(0)} days to pay on average, against ${col.collection_days_prior.toFixed(0)} before. Standard terms are ${col.standard_terms_days} days.`
            : undefined,
        facts: owing.slice(0, 2).map((b) => ({
          label: b.customer,
          value: `${murCompact(b.open_amount)} open${b.overdue_amount ? ` · ${murCompact(b.overdue_amount)} overdue` : ''}`,
          tone: b.overdue_amount ? 'warn' : undefined,
        })),
        visual: owing.length
          ? {
              type: 'bars',
              label: 'Open invoices by customer',
              rows: owing.map((b) => ({ label: b.customer, value: b.open_amount, display: murCompact(b.open_amount) })),
              color: 'var(--color-actual)',
            }
          : undefined,
        sources: [src('Invoices', 'Recorded invoices, actual', asOf, '/insights')],
        followUps: ['Which customers bring in the most?', 'How much cash do we have?'],
      }
    }
    case 'customers':
    case 'suppliers': {
      if (!ins) return needs(`${intent === 'customers' ? 'customer' : 'supplier'} breakdown`, '/insights')
      const conc = intent === 'customers' ? ins.customer_concentration : ins.supplier_concentration
      if (!conc || !conc.top.length) return noData(intent)
      const who = intent === 'customers' ? 'customer' : 'supplier'
      const top = conc.top[0]
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `${top.name} is the largest named ${who}: ${top.share_pct.toFixed(0)}% of ${intent === 'customers' ? 'income' : 'purchases'} in the last ${conc.days} days.`,
        body:
          `The top three named ${who}s make up ${conc.top3_share_pct.toFixed(0)}%.` +
          (conc.unidentified_amount > 0
            ? ` ${murCompact(conc.unidentified_amount)} is ${conc.unidentified_label.toLowerCase()} with no named ${who}.`
            : ''),
        facts: [
          { label: top.name, value: `${murCompact(top.amount)} · ${top.share_pct.toFixed(0)}%` },
          { label: `Top three ${who}s`, value: `${conc.top3_share_pct.toFixed(0)}%`, tone: conc.top3_share_pct >= 60 ? 'warn' : undefined },
        ],
        visual: {
          type: 'bars',
          label: `${intent === 'customers' ? 'Income' : 'Purchases'} by ${who}, last ${conc.days} days`,
          rows: conc.top.slice(0, 5).map((t) => ({ label: t.name, value: t.amount, display: `${t.share_pct.toFixed(0)}%` })),
          color: intent === 'customers' ? 'var(--color-actual)' : 'var(--color-expense)',
        },
        sources: [src(`${who[0].toUpperCase()}${who.slice(1)} concentration`, `Ledger, actual, last ${conc.days} days`, asOf, '/insights')],
        followUps:
          intent === 'customers'
            ? ['Which customers owe us the most?']
            : ['Where does most of the money go?', 'Why did gross margin change?'],
      }
    }
    case 'recurring': {
      if (!ins) return needs('recurring costs', '/insights')
      const rec = (ins.recurring ?? []).filter((r) => r.active).sort((a, b) => b.monthly_run_rate - a.monthly_run_rate)
      if (!rec.length) return noData(intent)
      const total = rec.reduce((s, r) => s + r.monthly_run_rate, 0)
      const fresh = rec.filter((r) => r.is_new)
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `${rec.length} recurring payments add up to about ${murCompact(total)} a month.`,
        body: fresh.length
          ? `${fresh.length} of them started recently: ${fresh
              .slice(0, 3)
              .map((r) => r.name)
              .join(', ')}.`
          : undefined,
        facts: rec.slice(0, 3).map((r) => ({ label: r.name, value: `${murCompact(r.monthly_run_rate)} / month` })),
        visual: {
          type: 'bars',
          label: 'Largest recurring payments, per month',
          rows: rec.slice(0, 5).map((r) => ({ label: r.name, value: r.monthly_run_rate, display: murCompact(r.monthly_run_rate) })),
          color: 'var(--color-expense)',
        },
        sources: [src('Recurring payments', 'Detected from repeated ledger payments, actual', asOf, '/insights')],
        followUps: ['Where does most of the money go?', 'What is the biggest opportunity?'],
      }
    }
    case 'product_lines': {
      if (!ins) return needs('product line figures', '/insights')
      const lines = (ins.product_lines ?? []).slice().sort((a, b) => b.revenue - a.revenue)
      if (!lines.length) return noData(intent, 'Sales are not recorded by product line for this business.')
      const growing = lines.filter((l) => l.change_pct !== null).sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0))[0]
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `${lines[0].line} brings in the most: ${lines[0].share_pct.toFixed(0)}% of product revenue in the last three months.`,
        body: growing ? `${growing.line} changed the most against the three months before: ${pct(growing.change_pct)}.` : undefined,
        facts: lines.slice(0, 3).map((l) => ({ label: l.line, value: `${murCompact(l.revenue)} · ${pct(l.change_pct)}` })),
        visual: {
          type: 'bars',
          label: 'Revenue by product line, last three months',
          rows: lines.map((l) => ({ label: l.line, value: l.revenue, display: murCompact(l.revenue) })),
          color: 'var(--color-actual)',
        },
        sources: [src('Product lines', 'Ledger, actual, last three months', asOf, '/insights')],
        followUps: ['How did revenue change recently?', 'What was our best month?'],
      }
    }
    case 'opportunity':
    case 'risk': {
      if (!c.opportunities) return needs('findings', '/opportunities')
      const kinds = intent === 'opportunity' ? GAIN_KINDS : RISK_KINDS
      const list = opps.filter((o) => kinds.includes(o.impact_kind)).sort((a, b) => (b.impact_high ?? 0) - (a.impact_high ?? 0))
      if (!list.length)
        return {
          status: 'empty',
          intent,
          headline: intent === 'opportunity' ? 'There is no open opportunity right now.' : 'There is no open risk right now.',
          body: 'New findings appear when data is imported and the engine runs again.',
          facts: [],
          sources: [{ label: 'Findings', detail: 'Opportunity engine', to: '/opportunities' }],
          followUps: ['How much cash do we have?'],
        }
      const a = findingAnswer(list[0], intent, intent === 'opportunity' ? 'Biggest opportunity' : 'Biggest risk')
      if (list.length > 1)
        a.visual = {
          type: 'bars',
          label: intent === 'opportunity' ? 'Open opportunities, upper estimate per year' : 'Open risks, money exposed (upper estimate)',
          rows: list.slice(0, 4).map((o) => ({ label: o.title, value: o.impact_high ?? 0, display: murCompact(o.impact_high) })),
          color: intent === 'opportunity' ? 'var(--color-gain)' : 'var(--color-coral-600)',
        }
      return a
    }
    case 'priorities': {
      if (!c.opportunities) return needs('findings', '/opportunities')
      const ranked = [...opps].sort((a, b) => b.priority_score - a.priority_score).slice(0, 3)
      if (!ranked.length)
        return {
          status: 'empty',
          intent,
          headline: 'Nothing is waiting for a decision.',
          body: 'New findings appear after each import.',
          facts: [],
          sources: [{ label: 'Findings', detail: 'Opportunity engine', to: '/opportunities' }],
          followUps: ['How much cash do we have?', 'How reliable is the data?'],
        }
      return {
        status: 'answer',
        intent,
        headline: `The engine ranks these ${ranked.length} open findings highest. You decide what to act on.`,
        body: 'Ranking combines severity, money at stake and confidence. It is an ordering of evidence, not an instruction.',
        facts: ranked.map((o, i) => ({ label: `${i + 1}. ${o.title}`, value: range(o), tone: o.kind === 'risk' ? 'bad' : 'good' })),
        sources: [{ label: 'Findings', detail: `Opportunity engine, data to ${date(ranked[0].data_as_of)}`, to: '/opportunities' }],
        followUps: ['What is the biggest risk?', 'Did the actions work?'],
      }
    }
    case 'outcomes': {
      if (!c.opportunities) return needs('findings', '/opportunities')
      const tracked = c.opportunities.filter((o) => ['in_progress', 'completed'].includes(o.status) && o.outcome)
      if (!tracked.length)
        return {
          status: 'empty',
          intent,
          headline: 'No action is being measured yet.',
          body: 'When you start an action from a finding, Valora freezes its target figure and re-measures it on later data.',
          facts: [],
          sources: [{ label: 'Findings', detail: 'Opportunity engine', to: '/opportunities' }],
          followUps: ['What should I look at first?'],
        }
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `${tracked.length} action${tracked.length > 1 ? 's are' : ' is'} being measured.`,
        body: 'Each result compares the same figure before and after the action started. It is evidence, not proof of cause.',
        facts: tracked.slice(0, 3).map((o) => ({
          label: o.title,
          value: o.outcome?.message ?? o.outcome?.status ?? '',
          tone: o.outcome?.status === 'achieved' ? 'good' : o.outcome?.status === 'worsened' ? 'bad' : undefined,
        })),
        sources: [{ label: 'Action results', detail: 'Re-measured from the ledger', to: '/opportunities' }],
        followUps: ['What should I look at first?'],
      }
    }
    case 'data_health': {
      const h = c.health
      if (!h) return needs('data health report', '/data-health')
      if (h.score === null || h.score === undefined) return noData(intent)
      const warnings = h.checks.filter((x) => x.status === 'warning')
      return {
        status: 'answer',
        intent,
        headline: `Data health is ${h.score}/100${warnings.length ? `, with ${warnings.length} thing${warnings.length > 1 ? 's' : ''} to review` : ''}.`,
        body: h.pending_changes
          ? `${h.pending_changes} suggested correction${h.pending_changes > 1 ? 's are' : ' is'} waiting for approval. Nothing is changed without a person approving it.`
          : 'No corrections are waiting for approval.',
        facts: warnings.slice(0, 3).map((w) => ({ label: w.label, value: w.detail, tone: 'warn' as const })),
        sources: [src('Data health', 'Checks on recorded transactions', h.as_of, '/data-health')],
        followUps: ['How much cash do we have?', 'What should I look at first?'],
      }
    }
    case 'monthly_story': {
      const months = complete(ov?.monthly ?? [])
      if (!months.length) return noData(intent)
      const last = months[months.length - 1]
      return {
        status: 'answer',
        intent,
        kind: 'actual',
        headline: `In ${monthLabel(last.month)}, revenue was ${murCompact(last.revenue)} and expenses ${murCompact(last.expenses)}.`,
        body: `Net cash flow that month: ${murCompact(last.net_cash_flow, true)}.`,
        facts: [
          { label: 'Revenue', value: murCompact(last.revenue) },
          { label: 'Expenses', value: murCompact(last.expenses) },
          { label: 'Net cash flow', value: murCompact(last.net_cash_flow, true), tone: last.net_cash_flow < 0 ? 'bad' : 'good' },
        ],
        visual: {
          type: 'spark',
          values: months.map((m) => m.net_cash_flow),
          label: 'Net cash flow by month',
          caption: 'Net cash flow by full month',
        },
        sources: [src('Monthly figures', 'Ledger, actual', asOf, '/')],
        followUps: ['What was our best month?', 'Why did gross margin change?'],
      }
    }
  }
}

function noData(intent: string, body = 'There is not enough recorded data to answer this yet.'): Answer {
  return {
    status: 'empty',
    intent,
    headline: 'There is no data for this yet.',
    body,
    facts: [],
    sources: [],
    followUps: ['How much cash do we have?'],
  }
}

function isEmptyBusiness(c: InsightContext) {
  return !!c.overview && c.overview.monthly.length === 0
}

/** Answer a question, or explain why it cannot be answered from Valora's data. */
export function answer(question: string, c: InsightContext, ctx?: AskContext): Answer {
  if (ctx?.type === 'finding') {
    const o = c.opportunities?.find((x) => x.id === ctx.id)
    if (o) return findingAnswer(o, 'finding')
  }
  if (ctx?.type === 'chart') {
    const intent: Intent = { cash: 'cash_outlook', monthly: 'monthly_story', kpis: 'revenue', worth: 'opportunity' }[ctx.chart] as Intent
    return guard(answerFor(intent, c), c)
  }
  const matched = matchIntent(question)
  const out = classifyOutOfScope(question, matched)
  if (out) return out
  return guard(answerFor(matched as Intent, c), c)
}

function guard(a: Answer, c: InsightContext): Answer {
  if (isEmptyBusiness(c) && a.intent !== 'data_health')
    return {
      status: 'empty',
      intent: 'no_data',
      headline: `${c.businessName} has no transactions in Valora yet.`,
      body: 'Import your bank or card export as a CSV in Data Health. Answers appear as soon as the data is checked and committed.',
      facts: [],
      sources: [{ label: 'Import data', detail: 'Data Health, import', to: '/data-health?tab=import' }],
      followUps: [],
    }
  return a
}
