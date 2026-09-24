# 2026-09-23 — Full browser test of the running site, and the fixes it led to

Author: Claude

Tested in Chrome on the running site (started 15:12): the overview, `/delivery`, `/reviews`, `/sellers`, `/help` and an unknown page. AI requests were spaced 20 s apart at the user's request.

Working:
- Tabs: Evidence opens first, and switching keeps each panel's content.
- Overview suggestion: AI answer and 5 charts. Overview caveats: 6 charts.
- The chart-kind switcher (line, area, bars) and the example chips.
- One scroll area for the whole conversation; single messages do not scroll.
- Delivery suggestion and caveats: AI answers with 2 charts each. Reviews and sellers pages load with their charts and evidence. Help is fine: the three `${` found in its source are inside its page scripts.
- A missing page answers 404. No script errors on any page.

Bugs found and fixed:
- The overview caveats fell back to the fixed text (`unsupported_numbers: 461`): the model wrote 461,022 as "461 k". `NumberCheck.scaledFromEvidence` now accepts a figure followed by k, thousand, million or m only when it is a correct rounding of a given figure; "90 k" or a bare "461" are still rejected (`NumberCheckTest`).
- The delivery caveats called the late-delivery rate "higher" when it fell from 10.1% to 3.6%. `TrendCaveatWriter.evidence` now starts with the measure's direction ("The late-delivery rate improved: …, lower is better") and tells the model never to describe it the other way (`TrendCaveatWriterTest`). The follow-up chat gets the same line.
- In Bars mode, the forecast's low and high edges were drawn as bars of their own. Those series are now marked `range` (`PanelTools.range`) and drawn as thin dashed lines, and left out of bar mode (`MosaicCharts.render`).
- The example questions were the overview's on every page. `EXAMPLES` in `panels.js` is now per page (overview, delivery, reviews, sellers) and per tab.
- The live site's text used "Observed gross item sales", which the user found unclear. Visible chart captions now say "Recorded sales: item prices in BRL, before freight".

Not fixed yet:
- The two questions that need the new tools (`salesMix`, `compareCategories`) failed with `llm_unreachable: AIException`, 15 to 20 s apart, while the older forecast tool worked.
  - Suspected cause: Groq's 8,000-tokens-per-minute free tier, since the 22 tool descriptions and a 1,500-token reply budget make each tool question cost far more.
  - `PanelChat`'s reply budget was cut from 1,500 to 900 tokens in `config/ai/agents.json`.
  - The exact error is needed from the site's console to confirm.
- Not verified yet: all fixes above need a site restart.
- Verified: both Java modules' tests pass; `node --check` passes on `panels.js` and `charts.js`.
