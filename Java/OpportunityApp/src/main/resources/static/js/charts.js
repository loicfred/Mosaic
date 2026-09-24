// Draws what the page already rendered from the API; no metric is computed here.
(() => {
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const BRL_PER_USD = 3.33;
  const brl = v => '$' + Math.round(v / BRL_PER_USD).toLocaleString('en-US');
  const pct = v => (v * 100).toFixed(1) + '%';
  const pad = n => Array(Math.max(n, 0)).fill(null);
  const num = v => Number(v).toLocaleString('en-US', { maximumFractionDigits: 1 });
  const fmt = y => ({ rate: pct, count: num, days: v => num(v) + ' days' })[y] || brl;
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
    context(id, months) {
      const chart = window.Chart?.getChart(id);
      if (!chart) return;
      chart.$externalContext = months;
      chart.options.plugins.tooltip.callbacks.afterBody = items => months?.[items[0]?.label] || [];
      if (!chart.$contextPlugin) {
        chart.$contextPlugin = true;
        chart.config.plugins.push({id: 'externalContextMarkers', afterDraw(c) {
          if (!c.$externalContext) return;
          const {ctx, chartArea, scales} = c;
          ctx.save(); ctx.strokeStyle = css('--muted'); ctx.setLineDash([2, 5]);
          c.data.labels.forEach((month, i) => {
            if (!c.$externalContext[month]?.length) return;
            const x = scales.x.getPixelForValue(i);
            ctx.beginPath(); ctx.moveTo(x, chartArea.top); ctx.lineTo(x, chartArea.bottom); ctx.stroke();
          });
          ctx.restore();
        }});
      }
      chart.update();
    },
    sales(id, months, forecast) {
      if (!months) return;
      const f = (forecast && forecast.forecast) || [], b = (forecast && forecast.baselines) || {};
      const s = withPrediction(months, f, 'sales'), pred = css('--predicted');
      const sets = [line('Sales, observed', s.obs, css('--observed'))];
      if (f.length) {
        const method = forecast.forecast_method === 'naive_last' ? 'Same as last month forecast' : forecast.forecast_method === 'mean_last_3' ? 'Average of last 3 months forecast' : 'Model forecast';
        sets.push(line(method, s.joined, pred, { borderDash: [6, 4], pointRadius: 3 }));
        sets.push(line('_upper', s.after(f.map(p => p.upper)), 'transparent', { pointRadius: 0, fill: '+1', backgroundColor: pred + '22' }));
        sets.push(line('_lower', s.after(f.map(p => p.lower)), 'transparent', { pointRadius: 0 }));
        if (b.naive_last && forecast.forecast_method !== 'naive_last') sets.push(line('Same as last month', s.after(b.naive_last.map(p => p.sales)), css('--muted'), { borderWidth: 1, pointRadius: 0, borderDash: [2, 3] }));
        if (b.mean_last_3 && forecast.forecast_method !== 'mean_last_3') sets.push(line('Average of last 3 months', s.after(b.mean_last_3.map(p => p.sales)), css('--chart-baseline'), { borderWidth: 1, pointRadius: 0, borderDash: [8, 3, 2, 3] }));
      }
      draw(id, s.labels, sets, 'brl', c => c.datasetIndex === 0 && months[c.dataIndex] ? `Orders: ${months[c.dataIndex].orders.toLocaleString('en-US')}` : '');
    },
    // one line per named series, on the union of their months; a month a series lacks is a gap, not a zero
    lines(id, named, y) {
      if (!named || !named.length) return;
      const labels = [...new Set(named.flatMap(n => n.points.map(p => p.month)))].sort();
      const sets = named.map((n, i) => {
        const byMonth = new Map(n.points.map(p => [p.month, p.value]));
        return line(n.label, labels.map(m => byMonth.has(m) ? byMonth.get(m) : null), css(n.color || `--series-${i % 3 + 1}`));
      });
      draw(id, labels, sets, y);
    },
    // A chart the site sent with a chat answer, drawn as `kind` (one of spec.kinds): line, area or bar for values over
    // months; bar or hbar to compare; doughnut or pie for the parts of one whole. Returns the chart so it can be redrawn.
    render(id, spec, kind) {
      const el = document.getElementById(id);
      if (!el || !window.Chart) return null;
      const existing = Chart.getChart(el);
      if (existing) existing.destroy();
      const f = fmt(spec.unit), color = i => css(`--series-${i % 4 + 1}`);
      let labels, datasets;
      if (spec.shape === 'time') {
        // a forecast's low and high edges are a range, not values of their own: dashed lines, and no bars
        const shown = spec.series.filter(s => !(s.range && kind === 'bar'));
        labels = [...new Set(shown.flatMap(s => s.points.map(p => p.month)))].sort();
        datasets = shown.map((s, i) => {
          const byMonth = new Map(s.points.map(p => [p.month, p.value])), edge = !!s.range, c = edge ? css('--muted') : color(i);
          return { label: s.label, data: labels.map(m => byMonth.has(m) ? byMonth.get(m) : null), borderColor: c,
            backgroundColor: kind === 'area' && !edge ? c + '33' : c, fill: kind === 'area' && !edge, pointRadius: edge ? 0 : 2,
            borderWidth: edge ? 1 : 2, borderDash: edge ? [4, 4] : [], spanGaps: false };
        });
      } else {
        labels = spec.labels;
        const round = kind === 'pie' || kind === 'doughnut';
        datasets = spec.series.map((s, i) => ({ label: s.label, data: s.values,
          backgroundColor: round ? labels.map((_, j) => color(j)) : color(i), borderColor: round ? css('--bg-card') : color(i) }));
      }
      const round = kind === 'pie' || kind === 'doughnut';
      return new Chart(el, {
        type: round ? kind : kind === 'hbar' ? 'bar' : kind === 'area' ? 'line' : kind,
        data: { labels, datasets },
        options: {
          maintainAspectRatio: false, animation: false, indexAxis: kind === 'hbar' ? 'y' : 'x',
          interaction: round ? undefined : { mode: 'index', intersect: false },
          scales: round ? {} : {
            [kind === 'hbar' ? 'x' : 'y']: { ticks: { callback: f }, beginAtZero: spec.unit !== 'brl' || kind !== 'line' },
            [kind === 'hbar' ? 'y' : 'x']: { grid: { display: false } }
          },
          plugins: {
            legend: { display: round || datasets.length > 1, position: round ? 'right' : 'top' },
            tooltip: { filter: i => i.raw !== null, callbacks: { label: c => `${round ? c.label : c.dataset.label}: ${f(c.raw)}` } }
          }
        }
      });
    },
    // grouped bars: one group per label, one bar per dataset; missing values are left out, not drawn as zero
    bars(id, labels, named, y) {
      const el = document.getElementById(id);
      if (!el || !window.Chart || !labels.length) return;
      new Chart(el, {
        type: 'bar',
        data: { labels, datasets: named.map((n, i) => ({ label: n.label, data: n.values, backgroundColor: css(n.color || `--series-${i % 3 + 1}`) })) },
        options: {
          maintainAspectRatio: false, animation: false,
          scales: { y: { ticks: { callback: fmt(y) }, beginAtZero: true }, x: { grid: { display: false } } },
          plugins: { tooltip: { filter: i => i.raw !== null, callbacks: { label: c => `${c.dataset.label}: ${fmt(y)(c.raw)}` } } }
        }
      });
    }
  };
})();
