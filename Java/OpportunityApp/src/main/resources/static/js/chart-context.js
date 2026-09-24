(() => {
  async function load() {
    const control = document.getElementById('chart-context-control');
    if (!control) return;
    try {
      const response = await fetch('/api/chart-context', {headers: {Accept: 'application/json'}});
      if (!response.ok) return;
      const data = await response.json();
      if (!data.available) return;
      const chart = window.Chart?.getChart('sales-chart');
      if (!chart) return;
      const markers = {}, eventRows = data.events.events || [], economicRows = data.economy.months || [];
      const details = document.getElementById('chart-context-details'), list = document.getElementById('chart-context-list');
      const select = document.getElementById('chart-context-month'), toggle = document.getElementById('chart-context-toggle');
      chart.data.labels.forEach(month => {
        const entries = eventRows.filter(event => event.start?.slice(0, 7) <= month && event.end?.slice(0, 7) >= month)
          .map(event => ({text: `${event.name} (${event.kind}). ${event.note || ''}`, source: event.source}));
        const economy = economicRows.find(row => row.month === month);
        if (economy) Object.entries(data.economy.series || {}).forEach(([key, meaning]) => {
          if (economy[key] != null) entries.push({text: `${meaning}: ${economy[key]}. ${data.economy.source || ''}`});
        });
        if (!entries.length) return;
        markers[month] = entries.map(entry => 'External context: ' + entry.text);
        const option = document.createElement('option'); option.value = month; option.textContent = month; select.append(option);
        option.contextEntries = entries;
      });
      if (!select.options.length) return;
      const render = () => {
        list.replaceChildren();
        for (const entry of select.selectedOptions[0]?.contextEntries || []) {
          const item = document.createElement('li'); item.textContent = entry.text;
          if (entry.source && /^https?:\/\//.test(entry.source)) {
            const link = document.createElement('a'); link.href = entry.source; link.textContent = ' Source'; item.append(link);
          }
          list.append(item);
        }
      };
      select.addEventListener('change', render);
      toggle.addEventListener('change', () => {
        details.hidden = !toggle.checked;
        window.MosaicCharts.context('sales-chart', toggle.checked ? markers : null);
      });
      render(); control.hidden = false;
    } catch (_) { /* Optional context must never interrupt the business chart. */ }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load);
  else load();
})();
