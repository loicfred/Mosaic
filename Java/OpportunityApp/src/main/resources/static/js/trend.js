// The trend pages: draw the measure by month, and open the evidence, suggestion and caveat panels under it.
// Every figure comes from the API with the page or with a panel's answer; nothing is calculated here.
(() => {
  const readable = (name, group) => group === 'category' ? String(name).replace(/_/g, ' ') : String(name);
  const chart = (...args) => MosaicPanels.chart(...args);

  function adviceCharts(box, e) {
    const top = ((e && e.candidates) || []).slice(0, 3);
    if (!top.length) return;
    chart(box, `${e.label} of the suggested ${e.group_label === 'category' ? 'categories' : 'states'}`,
      `By purchase month. Each was suggested because it improved over the last 3 months against the 3 before, at least as much as the whole business.`,
      id => MosaicCharts.lines(id, top.map(c => ({ label: readable(c.name, e.group_label), points: c.series })), e.unit));
    const checks = Object.keys(top[0].checks || {});
    if (!checks.length) return;
    const names = { late_rate: 'Late-delivery rate', low_review_rate: 'Low-review rate (1 or 2 stars)' };
    chart(box, 'Checked against the whole business',
      `Last 3 months. A suggestion counts as ready only when each rate is no more than ${top[0].checks[checks[0]].tolerance_pp} points worse than the business. A missing bar means too few orders to judge.`,
      id => MosaicCharts.bars(id, top.map(c => readable(c.name, e.group_label)).concat('Whole business'), checks.map((k, i) => ({
        label: names[k] || k, values: top.map(c => c.checks[k].rate).concat(e.business_rates[k] ? e.business_rates[k].rate : null),
        color: `--series-${i + 2}`
      })), 'rate'));
  }

  function caveatCharts(box, e) {
    ((e && e.checks) || []).filter(c => c.triggered).forEach(c => {
      if (c.kind === 'change' && c.monthly.length)
        chart(box, c.title, `${c.comparison.label} by month. The caveat compares the last 3 months with the 3 before.`,
          id => MosaicCharts.lines(id, [{ label: c.comparison.label, points: c.monthly, color: '--series-3' }], c.comparison.unit));
      if (c.kind === 'groups' && c.groups.worst.length)
        chart(box, c.title, `${c.groups.label}: the ${c.groups.group_label === 'category' ? 'categories' : 'states'} that moved furthest the wrong way, before and after.`,
          id => MosaicCharts.bars(id, c.groups.worst.map(g => readable(g.name, c.groups.group_label)), [
            { label: '3 months before', values: c.groups.worst.map(g => g.previous.value), color: '--series-1' },
            { label: 'Last 3 months', values: c.groups.worst.map(g => g.recent.value), color: '--series-3' }
          ], c.groups.unit));
      if (c.kind === 'gap')
        chart(box, c.title, `${c.gap.label}, last 3 months. It shows the two go together, not that one causes the other.`,
          id => MosaicCharts.bars(id, [c.gap.worse.label, c.gap.better.label], [
            { label: c.gap.label, values: [c.gap.worse.value, c.gap.better.value], color: '--series-3' }
          ], c.gap.unit));
    });
  }

  window.MosaicTrend = {
    page(trend) {
      MosaicPanels.bind({ 'advice-panel': adviceCharts, 'caveats-panel': caveatCharts });
      if (!trend) return;
      MosaicCharts.lines('trend-chart', [{ label: `${trend.label}, observed`, points: trend.monthly, color: '--observed' }], trend.unit);
    }
  };
})();
