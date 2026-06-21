(function () {
    'use strict';

    const nav = document.querySelector('.report-nav');
    if (!nav) return;

    const buttons = nav.querySelectorAll('.report-nav__btn');
    const panels = document.querySelectorAll('.report-panel');

    function activate(tab) {
        buttons.forEach((b) => b.classList.toggle('is-active', b.dataset.tab === tab));
        panels.forEach((p) => {
            p.classList.toggle('is-active', p.id === 'panel-' + tab);
        });
    }

    buttons.forEach((btn) => {
        btn.addEventListener('click', () => activate(btn.dataset.tab));
    });

    window.getCookie = function (name) {
        const v = '; ' + document.cookie;
        const parts = v.split('; ' + name + '=');
        return parts[1] ? decodeURIComponent(parts[1].split(';')[0]) : '';
    };

    window.askAiToExplain = function (ctx, title, details, id, btn) {
        const box = document.getElementById(id);
        if (!box) return;
        if (!btn.dataset.orig) btn.dataset.orig = btn.innerHTML;

        if (box.classList.contains('is-visible') && box.dataset.loaded === '1') {
            box.classList.remove('is-visible');
            return;
        }

        box.classList.add('is-visible');
        box.innerHTML =
            '<div class="ai-response__head"><i class="fa-solid fa-sparkles"></i> AI Tutor</div>' +
            '<div class="ai-skeleton"><span></span><span></span><span></span><span></span></div>';
        btn.disabled = true;

        fetch('/ai-explain/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({
                context_type: ctx,
                item_title: title,
                item_details: details,
            }),
        })
            .then((r) => r.json())
            .then((d) => {
                btn.disabled = false;
                if (d.success) {
                    box.innerHTML =
                        '<div class="ai-response__head"><i class="fa-solid fa-sparkles"></i> AI Tutor</div>' +
                        '<div>' +
                        d.explanation +
                        '</div>';
                    box.dataset.loaded = '1';
                } else {
                    box.innerHTML = '<p>' + (d.error || 'Could not generate explanation.') + '</p>';
                    btn.innerHTML = btn.dataset.orig;
                }
            })
            .catch(() => {
                btn.disabled = false;
                box.innerHTML = '<p>Network error. Try again.</p>';
            });
    };

    window.copyToClipboard = function (id, btn) {
        const el = document.getElementById(id);
        if (!el) return;
        navigator.clipboard.writeText(el.innerText).then(() => {
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
            setTimeout(() => {
                btn.innerHTML = orig;
            }, 2000);
        });
    };

    window.downloadReport = function () {
        const t = document.title;
        document.title = 'CodeLens_Report_' + new Date().toISOString().slice(0, 10);
        document.querySelectorAll('.report-panel').forEach((p) => {
            p.classList.add('is-active');
            p.style.display = 'flex';
        });
        document.body.offsetHeight;
        window.print();
        document.querySelectorAll('.report-panel').forEach((p, i) => {
            if (i > 0) {
                p.classList.remove('is-active');
                p.style.display = '';
            }
        });
        document.title = t;
    };

    window.exportToPdf = window.downloadReport;
})();
