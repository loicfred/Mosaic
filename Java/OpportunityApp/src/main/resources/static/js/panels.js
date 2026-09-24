// The Evidence / Suggestion / Caveats tabs of the overview and the trend pages, and the follow-up questions under an
// AI answer. Each AI tab asks the site once per page load; a follow-up is answered from that tab's own figures,
// which the site fetches itself. No figure is calculated here.
(() => {
  const MAX_TURNS = 8; // the site accepts at most this many earlier messages

  function note(n) {
    return n.source === 'llm'
      ? `Written by an AI model (${n.model}) from the data. Every number it uses was checked against the data.`
      : 'Written from fixed rules on the data (the AI did not answer: ' + n.reason + ').';
  }

  function message(log, who, text, cls) {
    const p = document.createElement('p');
    p.className = `chat-msg ${who}${cls ? ' ' + cls : ''}`;
    p.textContent = text;
    log.append(p);
    log.scrollTop = log.scrollHeight;
    return p;
  }

  // a chart of the data a tool fetched for this answer, drawn under it; the site built it from the same API reply
  let charted = 0;
  function answerChart(log, spec) {
    const card = document.createElement('div'), heading = document.createElement('p'), caption = document.createElement('p'),
          frame = document.createElement('div'), canvas = document.createElement('canvas');
    card.className = 'chat-chart';
    heading.className = 'fw-semibold mb-0';
    heading.textContent = spec.title;
    caption.className = 'muted-note mb-1';
    caption.textContent = spec.caption;
    frame.className = 'chart short';
    canvas.id = 'answer-chart-' + (++charted);
    canvas.setAttribute('aria-label', spec.title);
    frame.append(canvas);
    card.append(heading, caption);
    // the chart kinds that suit this data, to switch between; the question may already have picked one
    const kinds = spec.kinds || [spec.kind];
    if (kinds.length > 1) {
      const picker = document.createElement('div');
      picker.className = 'chart-kinds';
      picker.setAttribute('aria-label', 'Chart type');
      kinds.forEach(kind => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn btn-sm btn-outline-light';
        b.textContent = KIND_NAMES[kind] || kind;
        b.setAttribute('aria-pressed', String(kind === spec.kind));
        b.addEventListener('click', () => {
          picker.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
          MosaicCharts.render(canvas.id, spec, kind);
        });
        picker.append(b);
      });
      card.append(picker);
    }
    card.append(frame);
    log.append(card);
    MosaicCharts.render(canvas.id, spec, spec.kind);
    log.scrollTop = log.scrollHeight;
  }
  const KIND_NAMES = { line: 'Line', area: 'Area', bar: 'Bars', hbar: 'Horizontal bars', pie: 'Pie', doughnut: 'Doughnut' };

  // examples to click instead of typing, so the owner sees what can be asked; each fills the box and sends it
  // per page (from the ask address: /api/overview/… or /api/trend/<measure>/…), then per tab
  const EXAMPLES = {
    overview: {
      'advice-panel': ['Show the sales forecast', 'Compare health beauty and housewares', 'Sales by payment type as a pie chart',
        'What if sales fall 10% for 3 months?', 'Which weekday sells the most?'],
      'caveats-panel': ['Show cancellations by month', 'Show the average order value by month', 'How are orders rated? As a doughnut',
        'What happened in November 2017?', 'How did the dollar move?']
    },
    delivery: {
      'advice-panel': ['Late deliveries by customer state', 'How many days does delivery take per state?', 'Show the delivery trend as bars',
        'Which sellers deliver late most often?'],
      'caveats-panel': ['Show freight share by month', 'What happened in May 2018?', 'Which open orders are most at risk of being late?',
        'Low reviews on late orders against on-time ones']
    },
    reviews: {
      'advice-panel': ['How are orders rated? As a pie chart', 'Low reviews by customer state', 'Show the low-review trend',
        'Compare health beauty and stationery'],
      'caveats-panel': ['Low reviews on late orders against on-time ones', 'Which delivered orders may get a low review?',
        'Show cancellations by month']
    },
    sellers: {
      'advice-panel': ['Show the active sellers trend', 'Sales by seller state as a doughnut', 'Which sellers deliver late most often?'],
      'caveats-panel': ['Show orders by weekday', 'Sales by category as horizontal bars', 'What if sales grow 20% for 3 months?']
    }
  };
  const pageOf = askUrl => (askUrl.match(/\/api\/trend\/(\w+)\//) || [null, 'overview'])[1];

  // an answer that used no tool still shows why: the panel's own main chart, attached under it
  function panelChart(log, drawPanel) {
    const scratch = document.createElement('div'), card = document.createElement('div'), note = document.createElement('p');
    // the page's chart helper names each canvas after its box's parent, so the card needs an id of its own
    card.id = 'panel-copy-' + (++charted);
    card.className = 'chat-chart';
    note.className = 'muted-note mb-1';
    note.textContent = "From this panel's figures:";
    card.append(note, scratch);
    log.append(card);
    drawPanel(scratch);
    [...scratch.children].slice(1).forEach(extra => extra.remove()); // the panel's first chart is its main evidence
    if (!scratch.children.length) card.remove();
  }

  // the box under an answer; the first answer opens the conversation the follow-ups continue
  function chatBox(panel, askUrl, firstAnswer, drawPanel) {
    const history = [{ role: 'assistant', text: firstAnswer }];
    const box = document.createElement('div'), log = document.createElement('div'), form = document.createElement('form');
    const input = document.createElement('input'), send = document.createElement('button');
    box.className = 'panel-chat mt-3';
    log.className = 'chat-log';
    log.setAttribute('aria-live', 'polite');
    form.className = 'd-flex gap-2 mod-form';
    input.className = 'form-control';
    input.maxLength = 500;
    input.autocomplete = 'off';
    input.placeholder = 'Ask a follow-up about this answer…';
    input.setAttribute('aria-label', 'Your follow-up question');
    send.type = 'submit';
    send.className = 'btn btn-outline-light';
    send.textContent = 'Ask';
    form.append(input, send);
    const examples = document.createElement('div');
    examples.className = 'chat-examples';
    const exampleList = (EXAMPLES[pageOf(askUrl)] || EXAMPLES.overview)[panel.id] || [];
    if (exampleList.length) {
      const label = document.createElement('p');
      label.className = 'chat-examples-label muted-note mb-1';
      label.textContent = 'Try asking:';
      examples.append(label);
    }
    exampleList.forEach(text => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'btn btn-sm btn-outline-light';
      chip.textContent = text;
      chip.addEventListener('click', () => { if (send.disabled) return; input.value = text; form.requestSubmit(); });
      examples.append(chip);
    });
    box.append(log, examples, form);
    panel.querySelector('.panel-chat-slot').append(box);

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const question = input.value.trim();
      if (!question || send.disabled) return;
      examples.hidden = true;
      message(log, 'you', question);
      const pending = message(log, 'bot', 'Reading the figures…', 'pending');
      input.value = '';
      send.disabled = input.disabled = true;
      try {
        const res = await fetch(askUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, history: history.slice(-MAX_TURNS) }) });
        const n = await res.json().catch(() => ({}));
        pending.classList.remove('pending');
        if (!res.ok) { pending.textContent = n.error || 'The question could not be answered.'; pending.classList.add('error'); return; }
        pending.textContent = n.text;
        if (n.source !== 'llm') { pending.classList.add(n.source === 'withheld' ? 'withheld' : 'error'); return; }
        history.push({ role: 'user', text: question }, { role: 'assistant', text: n.text });
        try {
          if (n.charts && n.charts.length) n.charts.forEach(spec => answerChart(log, spec));
          else if (drawPanel) panelChart(log, drawPanel);
        }
        catch (err) { console.error('Answer chart not drawn:', err); }
      } catch {
        pending.classList.remove('pending');
        pending.classList.add('error');
        pending.textContent = 'The site did not answer. Try again in a moment.';
      } finally {
        send.disabled = input.disabled = false;
        input.focus();
      }
    });
  }

  async function load(tab, panel, draw) {
    panel.dataset.requested = '1';
    const text = panel.querySelector('.panel-text'), noteEl = panel.querySelector('.panel-note');
    text.textContent = 'Asking the AI to read the figures…';
    noteEl.textContent = '';
    try {
      const res = await fetch(tab.dataset.url), n = await res.json();
      if (!res.ok) { text.textContent = (n.error || 'The figures could not be loaded.') + ' Reload the page to try again.'; return; }
      text.textContent = n.text;
      noteEl.textContent = note(n);
      // a chart that cannot be drawn must never hide the answer that did arrive
      try { if (draw) draw(panel.querySelector('.panel-charts'), n.evidence); }
      catch (err) { console.error('Evidence charts not drawn:', err); }
      if (tab.dataset.ask) chatBox(panel, tab.dataset.ask, n.text, draw ? box => draw(box, n.evidence) : null);
    } catch { text.textContent = 'The site did not answer. Reload the page to try again.'; }
  }

  // one titled chart appended to a panel's chart box; draw(canvasId) fills it from figures the API returned
  function chart(box, title, caption, draw) {
    const card = document.createElement('div'), heading = document.createElement('h4'), note = document.createElement('p'),
          frame = document.createElement('div'), canvas = document.createElement('canvas');
    card.className = 'mt-3';
    heading.className = 'fs-6 fw-semibold mb-1';
    heading.textContent = title;
    note.className = 'muted-note mb-2';
    note.textContent = caption;
    frame.className = 'chart short';
    canvas.id = 'evidence-' + box.childElementCount + '-' + box.parentElement.id;
    canvas.setAttribute('aria-label', title);
    frame.append(canvas);
    card.append(heading, note, frame);
    box.append(card);
    draw(canvas.id);
  }

  window.MosaicPanels = {
    chart,

    // charts: { 'advice-panel': fn(box, evidence), 'caveats-panel': fn(box, evidence) }
    bind(charts) {
      const tabs = [...document.querySelectorAll('[data-panel]')];
      if (!tabs.length) return;
      tabs[0].parentElement.setAttribute('role', 'tablist');
      const show = active => tabs.forEach(tab => {
        const on = tab === active, panel = document.getElementById(tab.dataset.panel);
        tab.setAttribute('aria-selected', String(on));
        tab.classList.toggle('active', on);
        panel.hidden = !on;
        if (on && tab.dataset.url && !panel.dataset.requested) load(tab, panel, charts[tab.dataset.panel]);
      });
      tabs.forEach(tab => {
        tab.setAttribute('role', 'tab');
        tab.removeAttribute('aria-expanded');
        document.getElementById(tab.dataset.panel).setAttribute('role', 'tabpanel');
        tab.addEventListener('click', () => show(tab));
      });
      show(tabs[0]);
    }
  };
})();
