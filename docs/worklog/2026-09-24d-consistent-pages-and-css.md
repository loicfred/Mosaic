# 2026-09-24 — Consistent page names, one data-page layout, CSS clean-up

Author: Claude

Names: the four data pages are named after what they measure and match their URLs: Sales (`/`), Delivery, Reviews, Sellers (`Measure` titles changed; its unused `icon` removed). Sidebar, footer, breadcrumbs (home crumb is now "Mosaic") and the Help guide use the same names. The AI tab on every page is "Suggested opportunity" (the Sales page said "Suggested investment").

Structure: `index.html` + `fragments/index/sales.html` became `sales.html` + `fragments/sales/page.html` + `static/js/sales.js`, mirroring `trend.html` + `fragments/trend/page.html` + `trend.js`; `OverviewController` became `SalesController`. Both pages use `fragments/items/pages.html` (page switcher) and `fragments/items/panels.html` (tab strip and the two answer panels). The chart helper both pages had copied is `MosaicPanels.chart` in `panels.js`. API URLs (`/api/overview/...`) are unchanged.

Look: page head is the question (Bricolage Grotesque) and its answer, with each figure underlined in its marker colour (solid teal observed, dashed lavender forecast). Body text is Atkinson Hyperlegible Next. Both fonts are bundled in `static/fonts/` (OFL, see its README) so the demo stays offline; `/fonts/**` is allowed before sign-in in `SecurityConfig` and skipped by the logger in `WebConfig`. The tabs are an underline strip matching Help's. The decorative hero gradient and blurred circle were removed.

Removed at the user's request: the header's "Observed / Model prediction / Hypothetical" key (`fragments/items/statekey.html`), which looked like links but went nowhere; the markers are still explained on the Help page.

CSS: removed rules for deleted pages (`mod-links`, `mod-tiles`, `mod-stat(s)`, `mod-nav`, `mod-bar-*`, `mod-icon`, `mod-empty`, `mod-panel`, `mod-tab-body`, `.controls`, `.verdict.on`, `.evidence dl`, `#resultBox`), duplicates (`.narrative` = `.panel-text`, two `.mod-tile-num`) and the rule that forced every text colour inside `.mod-page` (Bootstrap now reads the palette through `--bs-*` variables). The sidebar and breadcrumb styles moved from inline `<style>` blocks into `main.css`. `mod-hero` / `statement` / `lede` still work as aliases because Codex's in-progress `explore.html` and `what-if.html` use them.

Verified: `OpportunityImpl` `mvnw.cmd -o install` passed; `OpportunityApp` `mvnw.cmd -o test` 31 tests passed, `PagesRenderTest` included. Chrome at desktop width: Sales and Delivery render with the live API, the tabs switch, and the forecast table's range now wraps inside its card. Not checked: phone width (the window would not resize).
