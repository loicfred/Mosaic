(() => {
  const form = document.getElementById('what-if-form');
  if (!form) return;
  const change = document.getElementById('scenario-change');
  const status = document.getElementById('scenario-status');
  const results = document.getElementById('scenario-results');
  const number = value => typeof value === 'number' ? value.toLocaleString(undefined, {maximumFractionDigits: 2}) : 'Unavailable';
  change.addEventListener('input', () => { document.getElementById('change-label').textContent = `${change.value}%`; });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const button = form.querySelector('button');
    button.disabled = true;
    status.textContent = 'Calculating scenario�';
    results.hidden = true;
    try {
      const response = await fetch('/api/what-if', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
        horizon: Number(document.getElementById('scenario-horizon').value), salesChangePct: Number(change.value),
        category: document.getElementById('scenario-category').value || null, useModel: document.getElementById('scenario-summary').checked
      })});
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'The scenario could not be calculated. Check your inputs and try again.');
      const s = body.evidence, b = s.baseline, c = s.consequences;
      if (!c) { status.textContent = 'There is not enough recent activity for this scenario.'; return; }
      const held = c.late.rate_held;
      const usd = v => typeof v === 'number' ? v / 3.33 : v;
      const rows = [
        ['Gross item sales ($)', usd(b.monthly_sales), usd(c.projected_monthly_sales)],
        ['Orders', b.monthly_orders, c.projected_monthly_orders],
        ['Late orders', b.monthly_late_orders, held?.expected_late_per_month],
        ['Low reviews', b.monthly_low_reviews, held?.expected_low_reviews_per_month],
        ['Sellers above their observed peak', b.sellers_at_capacity?.count, c.sellers_at_capacity.count]
      ];
      const table = document.getElementById('scenario-comparison');
      table.replaceChildren();
      for (const row of rows) {
        const tr = document.createElement('tr');
        row.forEach((value, index) => { const cell = document.createElement(index ? 'td' : 'th'); cell.textContent = index ? number(value) : value; tr.append(cell); });
        table.append(tr);
      }
      document.getElementById('scenario-period').textContent = `Baseline: ${b.months.join(', ')}. Hypothetical horizon: ${s.scenario.horizon} months. Active sellers: ${c.sellers_at_capacity.active_sellers}.`;
      document.getElementById('scenario-narrative').textContent = body.narrative.text;
      document.getElementById('scenario-source').textContent = body.narrative.source === 'llm' ? 'AI wording checked against the calculated evidence.' : 'Calculated summary; AI was not used.';
      const assumptions = document.getElementById('scenario-assumptions');
      assumptions.replaceChildren();
      [...s.assumptions, ...s.limitations].forEach(text => { const li = document.createElement('li'); li.textContent = text; assumptions.append(li); });
      results.hidden = false;
      status.textContent = 'Scenario calculated.';
    } catch (error) { status.textContent = error.message || 'The analytics service is unavailable. Try again.'; }
    finally { button.disabled = false; }
  });
})();
