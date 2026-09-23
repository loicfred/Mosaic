// Draws what the page already rendered from the API; no metric is computed here.
(() => {
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const brl = v => 'BRL ' + Math.round(v).toLocaleString('en-US');
  const pct = v => (v * 100).toFixed(1) + '%';
  const pad = n => Array(Math.max(n, 0)).fill(null);
  const fmt = y => y === 'rate' ? pct : brl;
  if (window.Chart) {
    Chart.defaults.color = css('--text-color');
    Chart.defaults.borderColor = css('--chart-grid');
  }

  // legend keys drawn as short lines, dashed like their series; Chart.js drops the dash for line-style keys on its own
  const legendLines = chart => Chart.defaults.plugins.legend.labels.generateLabels(chart)
    .map(l => Object.assign(l, { lineDash: chart.data.datasets[l.datasetIndex].borderDash || [] }));

  function draw(id, labels, datasets, y, tooltipExtra) {
    const el = document.getElementById(id);
    if (!el || !window.Chart) return;
    new Chart(el, {
      type: 'line',
      data: { labels, datasets },
      options: {
        maintainAspectRatio: false, animation: false, interaction: { mode: 'index', intersect: false },
        scales: { y: { ticks: { callback: fmt(y) }, beginAtZero: y === 'rate' }, x: { grid: { display: false } } },
        plugins: {
          legend: { labels: { usePointStyle: true, pointStyle: 'line', pointStyleWidth: 26, generateLabels: legendLines, filter: i => !i.text.startsWith('_') } },
          tooltip: { filter: i => i.raw !== null && !i.dataset.label.startsWith('_'),
            callbacks: { label: c => `${c.dataset.label}: ${fmt(y)(c.raw)}`, afterLabel: tooltipExtra || (() => '') } }
        }
      }
    });
  }

  // observed values, then a prediction drawn from the last observed point so the two lines meet
  function withPrediction(observed, predicted, key) {
    const n = observed.length;
    const joined = predicted.length && n ? pad(n - 1).concat([observed[n - 1][key]], predicted.map(p => p[key])) : pad(n).concat(predicted.map(p => p[key]));
    return { labels: observed.map(o => o.month).concat(predicted.map(p => p.month)), obs: observed.map(o => o[key]).concat(pad(predicted.length)), joined, after: p => pad(n).concat(p) };
  }

  const line = (label, data, color, extra) => Object.assign({ label, data, borderColor: color, backgroundColor: color, pointRadius: 2, borderWidth: 2, tension: 0, spanGaps: false }, extra);

  window.MosaicCharts = {
    sales(id, months, forecast) {
      if (!months) return;
      const f = (forecast && forecast.forecast) || [], b = (forecast && forecast.baselines) || {};
      const s = withPrediction(months, f, 'sales'), pred = css('--predicted');
      const sets = [line('Sales, observed', s.obs, css('--observed'))];
      if (f.length) {
        sets.push(line('Model forecast', s.joined, pred, { borderDash: [6, 4], pointRadius: 3 }));
        sets.push(line('_upper', s.after(f.map(p => p.upper)), 'transparent', { pointRadius: 0, fill: '+1', backgroundColor: pred + '22' }));
        sets.push(line('_lower', s.after(f.map(p => p.lower)), 'transparent', { pointRadius: 0 }));
        if (b.naive_last) sets.push(line('Same as last month', s.after(b.naive_last.map(p => p.sales)), css('--muted'), { borderWidth: 1, pointRadius: 0, borderDash: [2, 3] }));
        if (b.mean_last_3) sets.push(line('Average of last 3 months', s.after(b.mean_last_3.map(p => p.sales)), css('--chart-baseline'), { borderWidth: 1, pointRadius: 0, borderDash: [8, 3, 2, 3] }));
      }
      draw(id, s.labels, sets, 'brl', c => c.datasetIndex === 0 && months[c.dataIndex] ? `Orders: ${months[c.dataIndex].orders.toLocaleString('en-US')}` : '');
    },
    category(id, series, forecast) {
      if (!series) return;
      const s = withPrediction(series, forecast || [], 'sales');
      const sets = [line('Sales, observed', s.obs, css('--observed'))];
      if (forecast && forecast.length) sets.push(line('Model forecast', s.joined, css('--predicted'), { borderDash: [6, 4], pointRadius: 3 }));
      draw(id, s.labels, sets, 'brl');
    },
    rate(id, monthly, key, label) {
      if (!monthly) return;
      draw(id, monthly.map(m => m.month), [line(label, monthly.map(m => m[key]), css('--observed'))], 'rate');
    }
  };
})();
