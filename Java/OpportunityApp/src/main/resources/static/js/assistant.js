// The chat box in the header: sends questions to /api/assistant and shows the checked replies.
(() => {
    const root = document.getElementById('assistant');
    if (!root) return;
    const panel = document.getElementById('assistant-panel'), log = document.getElementById('assistant-log');
    const form = document.getElementById('assistant-form'), input = document.getElementById('assistant-input');
    const openBtn = document.getElementById('assistant-open'), status = document.getElementById('assistant-status');
    // only the site's own evidence pages become links; everything else stays text
    const PAGE = /(\/(?:categories|scenario|risk)[^\s),]*|(?<=\s|^)\/(?=[\s.]|$))/g;

    const bubble = (cls, text) => {
        const p = document.createElement('p');
        p.className = 'assistant-msg ' + cls;
        text.split(PAGE).forEach((part, i) => {
            if (i % 2 === 0) { p.append(part); return; }
            const a = document.createElement('a');
            a.href = part.replace(/\.$/, '');
            a.textContent = part;
            p.append(a);
        });
        log.append(p);
        log.scrollTop = log.scrollHeight;
        return p;
    };

    const showStatus = async () => {
        try {
            const s = await (await fetch('/api/assistant/status')).json();
            status.textContent = !s.enabled ? 'Model switched off' : !s.reachable ? 'Model offline' : s.tools === false ? `${s.model} (no tool use)` : s.model;
        } catch { status.textContent = 'Status unknown'; }
    };

    const toggle = open => {
        panel.hidden = !open;
        openBtn.setAttribute('aria-expanded', String(open));
        if (open) { showStatus(); input.focus(); }
    };

    openBtn.addEventListener('click', () => toggle(panel.hidden));
    document.getElementById('assistant-close').addEventListener('click', () => toggle(false));
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) toggle(false); });
    document.getElementById('assistant-reset').addEventListener('click', async () => {
        await fetch('/api/assistant', {method: 'DELETE'});
        log.querySelectorAll('.assistant-msg').forEach(m => m.remove());
    });

    form.addEventListener('submit', async e => {
        e.preventDefault();
        const message = input.value.trim();
        if (!message) return;
        input.value = '';
        bubble('you', message);
        const wait = bubble('bot pending', 'Looking at the data… a local model can take a minute.');
        form.querySelector('button').disabled = true;
        try {
            const res = await fetch('/api/assistant', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message, context: root.dataset.context})});
            const body = await res.json();
            wait.remove();
            if (!res.ok) { bubble('bot error', body.error || 'The question could not be sent.'); return; }
            const reply = bubble('bot' + (body.verified ? '' : ' withheld'), body.text);
            if (body.verified && body.model) {
                const small = document.createElement('small');
                small.textContent = `Figures checked against the data. Model: ${body.model}`;
                reply.append(small);
            }
        } catch {
            wait.remove();
            bubble('bot error', 'The site did not answer. Check that it is still running.');
        } finally {
            form.querySelector('button').disabled = false;
            input.focus();
        }
    });
})();
