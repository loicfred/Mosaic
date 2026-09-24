// Presentation only: rates, totals, comparisons and exclusions come from Python.
(() => {
  const root = document.getElementById('explore-content'), data = window.exploreData;
  if (!root || !data) return;
  root.replaceChildren();
  const title = key => key.replaceAll('_', ' ').replace(/^./, c => c.toUpperCase());
  const money = new Set(['sales', 'freight', 'payment_total', 'average_order_value']);
  const rate = key => /rate|share/.test(key) && !/change_pp/.test(key);
  function format(key, value) {
    if (value == null) return 'Not available';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    if (typeof value !== 'number') return String(value);
    if (money.has(key)) return '$' + (value / 3.33).toLocaleString('en-US', {maximumFractionDigits: 2});
    if (rate(key) || key === 'relative_change') return (value * 100).toFixed(1) + '%';
    return value.toLocaleString('en-US', {maximumFractionDigits: 2}) + (key === 'change_pp' ? ' pp' : '');
  }
  function node(tag, text, parent, cls) {
    const el = document.createElement(tag); if (text != null) el.textContent = text;
    if (cls) el.className = cls; if (parent) parent.append(el); return el;
  }
  function card(heading, note) {
    const el = node('section', null, root, 'mod-card obs'); node('h2', heading, el);
    if (note) node('p', note, el); return el;
  }
  function facts(heading, values) {
    const box = card(heading), dl = node('dl', null, box, 'explore-facts');
    Object.entries(values || {}).forEach(([key, value]) => {
      const pair = node('div', null, dl); node('dt', title(key), pair); node('dd', format(key, value), pair, 'explore-detail');
    }); return box;
  }
  function table(heading, rows, keys, note, entityKind) {
    const box = card(heading, note);
    if (!rows?.length) { node('p', 'No eligible records are available for this view.', box); return; }
    const label = node('label', 'Filter these rows', box, 'explore-filter');
    const input = node('input', null, label); input.type = 'search'; input.placeholder = 'Type a month, name or value';
    const wrap = node('div', null, box, 'explore-table'); wrap.tabIndex = 0;
    wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', heading);
    const grid = node('table', null, wrap), head = node('tr', null, node('thead', null, grid));
    keys.forEach(key => { const th = node('th', title(key), head); th.scope = 'col'; });
    const body = node('tbody', null, grid);
    rows.forEach(row => {
      const tr = node('tr', null, body);
      keys.forEach(key => {
        const td = node('td', null, tr);
        if (key === 'name' && entityKind) {
          const a = node('a', row[key], td); a.href = '/entities/' + entityKind + '/' + encodeURIComponent(row[key]);
        } else node('span', format(key, row[key]), td);
      });
    });
    const status = node('p', '', box); status.setAttribute('role', 'status');
    input.addEventListener('input', () => {
      let visible = 0;
      [...body.rows].forEach(row => { row.hidden = !row.textContent.toLowerCase().includes(input.value.toLowerCase()); if (!row.hidden) visible++; });
      status.textContent = visible ? visible + ' rows shown' : 'No rows match this filter.';
    });
  }
  let charts = 0;
  function chart(heading, rows, fields, unit = 'brl', business) {
    if (!rows?.length) return;
    const box = card(heading), wrap = node('div', null, box, 'explore-chart'), canvas = node('canvas', null, wrap);
    canvas.id = 'explore-chart-' + charts++; canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', heading + '. Values are listed in the following table.');
    const series = fields.map(key => ({label: title(key), points: rows.map(row => ({month: row.month, value: row[key]}))}));
    if (business) series.push({label: 'Whole business', points: business.map(row => ({month: row.month, value: row[fields[0]]}))});
    window.MosaicCharts?.lines(canvas.id, series, unit);
  }
  switch (window.exploreSection) {
    case 'quality':
      facts('Coverage and missing values', data.summary);
      table('Order statuses', data.statuses, ['status', 'orders']);
      facts('Excluded records by calculation', data.exclusions);
      facts('Dataset checksums', data.dataset_hashes);
      break;
    case 'payments':
      chart('Recorded payments and item sales', data.monthly, ['payment_total', 'sales']);
      table('Monthly payments', data.monthly, ['month', 'orders', 'payment_orders', 'payment_total', 'sales', 'average_order_value', 'instalment_orders', 'instalment_share', 'average_installments', 'cancelled_orders', 'cancellation_rate'], 'Payment records are not bank cash flow. Item sales do not establish profit.');
      table('Payment value mix', data.payment_mix, ['month', 'payment_type', 'payment_total', 'payment_rows', 'share']);
      table('Predominant payment method per order', data.predominant_mix, ['month', 'payment_type', 'orders', 'share']);
      break;
    case 'freight':
      chart('Freight share over time', data.monthly, ['freight_share'], 'rate');
      table('Monthly freight', data.monthly, ['month', 'orders', 'sales', 'freight', 'freight_share']);
      facts('Comparison periods', {current_period: data.current_period, previous_period: data.previous_period});
      for (const key of ['categories', 'states']) table(title(key), data[key], ['name', 'orders', 'sales', 'freight', 'freight_share', 'previous_share', 'change_pp', 'relative_change', 'rising'], 'Freight burden is a recorded value ratio; it does not measure delivery cost or margin.', key === 'categories' ? 'category' : null);
      break;
    case 'cohorts':
      facts('Observation window', {observation_end: data.observation_end});
      table('Customers grouped by first purchase month', data.rows, ['cohort', 'customers', 'returning_customers', 'returning_share', 'followup_months', 'incomplete'], 'Recent cohorts have less time to return. Compare cohorts with equivalent follow-up; incomplete cohorts cannot establish lower retention.');
      break;
    case 'models':
      if (!data.rows?.length) node('p', 'No model metadata is available.', card('Model availability'));
      for (const model of data.rows || []) {
        facts(title(model.name), model);
      }
      break;
    case 'entities':
      table('Categories', data.categories, ['name', 'orders', 'sales'], 'Select a category to compare its trend with the business.', 'category');
      table('Sellers', data.sellers, ['name', 'orders', 'sales'], 'Select a seller to inspect recorded sales and delivery evidence.', 'seller');
      break;
    case 'entity':
      facts('Observed totals', data.summary);
      if (data.small_sample) node('p', 'Small sample: fewer than ' + data.minimum_orders + ' orders. Treat this comparison cautiously.', card('Limited support'));
      chart('Monthly sales compared with the business', data.monthly, ['sales'], 'brl', data.business_monthly);
      chart('Late-delivery rate compared with the business', data.monthly, ['late_rate'], 'rate', data.business_monthly);
      table('Entity monthly evidence', data.monthly, ['month', 'orders', 'sales', 'late_rate', 'low_review_rate']);
      table('Whole-business monthly evidence', data.business_monthly, ['month', 'orders', 'sales', 'late_rate', 'low_review_rate']);
      break;
  }
  if (data.limitations?.length) {
    const ul = node('ul', null, card('How to interpret this evidence'));
    data.limitations.forEach(text => node('li', text, ul));
  }
})();
