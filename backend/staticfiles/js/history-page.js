(function () {
    'use strict';

    const panel = document.getElementById('historyDetailPanel');
    const content = document.getElementById('historyDetailContent');
    if (!panel || !content) return;

    // ── Persistent cache: survives page navigation (page 1 ↔ page 2) ──────────
    const SESSION_KEY = 'cl_history_cache';
    const SESSION_MAX = 40; // max entries to keep in sessionStorage

    function cacheLoad() {
        try {
            return JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}');
        } catch (e) { return {}; }
    }

    function cacheSave(store) {
        try {
            sessionStorage.setItem(SESSION_KEY, JSON.stringify(store));
        } catch (e) { /* storage full — skip */ }
    }

    function cacheGet(id) {
        const store = cacheLoad();
        return store[id] || null;
    }

    function cacheSet(id, data) {
        const store = cacheLoad();
        store[id] = data;
        // Evict oldest entries if over limit
        const keys = Object.keys(store);
        if (keys.length > SESSION_MAX) {
            keys.slice(0, keys.length - SESSION_MAX).forEach(function (k) {
                delete store[k];
            });
        }
        cacheSave(store);
    }

    function cacheHas(id) {
        return !!cacheGet(id);
    }
    // ─────────────────────────────────────────────────────────────────────────

    let loadingId = null;
    let fetchController = null;
    let prefetchTimer = null;

    // Seed cache from server-embedded previews (current page items are free)
    const embeddedEl = document.getElementById('history-previews-data');
    if (embeddedEl) {
        try {
            const embedded = JSON.parse(embeddedEl.textContent);
            Object.keys(embedded).forEach(function (key) {
                if (!cacheHas(parseInt(key, 10))) {
                    cacheSet(parseInt(key, 10), embedded[key]);
                }
            });
        } catch (e) {
            /* ignore */
        }
    }

    function escapeHtml(t) {
        if (!t) return '';
        const d = document.createElement('div');
        d.textContent = t;
        return d.innerHTML;
    }

    function formatDate(iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch (e) {
            return '';
        }
    }

    function getCsrf() {
        const v = '; ' + document.cookie;
        const parts = v.split('; csrftoken=');
        return parts[1] ? decodeURIComponent(parts[1].split(';')[0]) : '';
    }

    function codeSection(data, id) {
        if (data.code_input) {
            return (
                '<p class="detail-preview-label">Source code' +
                (data.code_truncated ? ' (preview)' : '') +
                '</p>' +
                '<div class="code-panel" id="historyCodePanel"><pre>' +
                escapeHtml(data.code_input) +
                '</pre></div>'
            );
        }
        return (
            '<p class="detail-preview-label">Source code</p>' +
            '<div id="historyCodePanel" class="history-code-placeholder">' +
            '<button type="button" class="cl-btn cl-btn--ghost cl-btn--sm" id="btnLoadCode" data-id="' +
            id +
            '"><i class="fa-solid fa-code"></i> Load code preview</button>' +
            '</div>'
        );
    }

    function renderDetail(data, id) {
        const errItems = data.errors || [];
        const errList =
            errItems
                .map(function (e) {
                    return (
                        '<p style="font-size:0.85rem;margin-bottom:0.35rem">• <b>' +
                        escapeHtml(e.error_type) +
                        '</b>: ' +
                        escapeHtml(e.message || '') +
                        '</p>'
                    );
                })
                .join('') || '<p style="color:var(--cl-success)">✓ No errors detected</p>';

        const smellItems = data.code_smells || [];
        const smellList =
            smellItems
                .map(function (s) {
                    return (
                        '<p style="font-size:0.85rem;margin-bottom:0.35rem">• <b>' +
                        escapeHtml(s.smell_type) +
                        '</b></p>'
                    );
                })
                .join('') || '<p style="color:var(--cl-success)">✓ No smells detected</p>';

        const moreErrors =
            data.errors_truncated && data.error_count > errItems.length
                ? '<p style="font-size:0.78rem;color:var(--cl-text-subtle);margin-top:0.35rem">+' +
                  (data.error_count - errItems.length) +
                  ' more in full report</p>'
                : '';
        const moreSmells =
            data.smells_truncated && data.smell_count > smellItems.length
                ? '<p style="font-size:0.78rem;color:var(--cl-text-subtle);margin-top:0.35rem">+' +
                  (data.smell_count - smellItems.length) +
                  ' more in full report</p>'
                : '';

        const title = escapeHtml(data.title || 'Report #' + data.id);
        const star = '<span id="detailTitleStar" style="color:#eab308; margin-left:0.4rem">' +
            (data.is_starred ? '<i class="fa-solid fa-star"></i>' : '') +
            '</span>';

        return (
            '<header class="detail-header">' +
            '<div><h3>' +
            title +
            ' ' +
            star +
            '</h3>' +
            '<p style="color:var(--cl-text-muted);font-size:0.88rem;margin-top:0.35rem">' +
            formatDate(data.created_at) +
            '</p></div>' +
            '<div style="display:flex;gap:0.5rem;flex-wrap:wrap">' +
            '<button type="button" class="cl-btn cl-btn--ghost cl-btn--sm" id="btnStarDetail" data-id="' +
            id +
            '"><i class="' + (data.is_starred ? 'fa-solid fa-star' : 'fa-regular fa-star') + '" style="' + (data.is_starred ? 'color:#eab308' : '') + '"></i> ' + (data.is_starred ? 'Starred' : 'Star') + '</button>' +
            '<a href="/functionalities/?id=' +
            id +
            '&source=history" class="cl-btn cl-btn--primary cl-btn--sm">Full report <i class="fa-solid fa-arrow-right"></i></a>' +
            '</div></header>' +
            '<div class="detail-metrics">' +
            '<div class="metric-tile metric-tile--error"><strong>' +
            (data.error_count || 0) +
            '</strong><span>Errors</span></div>' +
            '<div class="metric-tile metric-tile--warn"><strong>' +
            (data.smell_count || 0) +
            '</strong><span>Smells</span></div>' +
            '<div class="metric-tile metric-tile--ok"><strong>' +
            (data.health_score || 0) +
            '</strong><span>' +
            escapeHtml(data.health_label || 'Score') +
            '</span></div>' +
            '</div>' +
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem">' +
            '<div style="padding:1rem;border-radius:12px;border:1px solid var(--cl-border);background:var(--cl-bg-muted)"><h4 style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--cl-text-subtle);margin-bottom:0.5rem">Errors</h4>' +
            errList +
            moreErrors +
            '</div>' +
            '<div style="padding:1rem;border-radius:12px;border:1px solid var(--cl-border);background:var(--cl-bg-muted)"><h4 style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--cl-text-subtle);margin-bottom:0.5rem">Smells</h4>' +
            smellList +
            moreSmells +
            '</div></div>' +
            codeSection(data, id)
        );
    }

    function bindStarButton(id, el) {
        const starBtn = document.getElementById('btnStarDetail');
        if (!starBtn || starBtn.dataset.bound === '1') return;
        starBtn.dataset.bound = '1';
        starBtn.addEventListener('click', function () {
            fetch('/api/analysis/' + id + '/star/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrf() },
            })
                .then(function (r) {
                    return r.json();
                })
                .then(function (res) {
                    if (res.success) {
                        // 1. Update session storage cache immediately
                        const cachedData = cacheGet(id);
                        if (cachedData) {
                            cachedData.is_starred = res.is_starred;
                            cacheSet(id, cachedData);
                        }

                        // 2. Toggle active star classes on the sidebar list element
                        if (el) {
                            el.classList.toggle('is-starred', res.is_starred);
                            const leftStarIcon = el.querySelector('.history-item__star');
                            if (leftStarIcon) {
                                leftStarIcon.classList.toggle('is-visible', res.is_starred);
                            }
                        }

                        // 3. Dynamically update detail panel title star span
                        const titleStar = document.getElementById('detailTitleStar');
                        if (titleStar) {
                            titleStar.innerHTML = res.is_starred ? '<i class="fa-solid fa-star"></i>' : '';
                        }

                        // 4. Dynamically update detail panel button icon, style & text
                        const icon = starBtn.querySelector('i');
                        if (icon) {
                            icon.className = res.is_starred ? 'fa-solid fa-star' : 'fa-regular fa-star';
                            icon.style.color = res.is_starred ? '#eab308' : '';
                        }
                        
                        // Update button text node safely
                        const textNodes = Array.from(starBtn.childNodes).filter(function (n) {
                            return n.nodeType === Node.TEXT_NODE;
                        });
                        if (textNodes.length > 0) {
                            textNodes[textNodes.length - 1].textContent = res.is_starred ? ' Starred' : ' Star';
                        }
                    }
                });
        });
    }

    function bindLoadCodeButton(id, data, el) {
        const btn = document.getElementById('btnLoadCode');
        if (!btn) return;
        btn.addEventListener('click', function () {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading…';
            fetchCode(id).then(function (updated) {
                cacheSet(id, updated);
                showDetail(updated, id, el);
            });
        });
    }

    function fetchCode(id, signal) {
        return fetch('/api/analysis/' + id + '/?summary=1&include_code=1', {
            signal: signal,
            credentials: 'same-origin',
            headers: { Accept: 'application/json' },
        })
            .then(function (r) {
                return r.json().then(function (body) {
                    if (!r.ok) {
                        throw new Error((body && body.error) || 'Could not load code');
                    }
                    return body;
                });
            });
    }

    function fetchSummary(id, signal) {
        return fetch('/api/analysis/' + id + '/?summary=1', {
            signal: signal,
            credentials: 'same-origin',
            headers: { Accept: 'application/json' },
        }).then(function (r) {
            return r.json().then(function (body) {
                if (!r.ok) {
                    throw new Error((body && body.error) || 'Request failed');
                }
                return body;
            });
        });
    }

    function showDetail(data, id, el) {
        content.innerHTML = renderDetail(data, id);
        content.classList.remove('is-swapping');
        content.classList.add('is-ready');
        bindStarButton(id, el);
        bindLoadCodeButton(id, data, el);
        // Code is only fetched when the user explicitly clicks "Load code preview"
        // — no hidden auto-fetch here, keeping each click to a single network request.
    }

    window.loadAnalysis = function (id, el) {
        document.querySelectorAll('.history-item').forEach(function (i) {
            i.classList.remove('is-active');
        });
        if (el) el.classList.add('is-active');

        // Instant render from sessionStorage cache — no network needed
        if (cacheHas(id)) {
            panel.classList.remove('is-loading');
            loadingId = id;
            showDetail(cacheGet(id), id, el);
            loadingId = null;
            return;
        }

        if (loadingId === id && panel.classList.contains('is-loading')) {
            return;
        }
        loadingId = id;

        const controller = new AbortController();
        if (fetchController) {
            fetchController.abort();
        }
        fetchController = controller;

        panel.classList.add('is-loading');
        content.classList.add('is-swapping');
        content.classList.remove('is-ready');
        content.innerHTML =
            '<div class="skeleton-detail"><div class="skeleton-block skeleton-block--lg"></div></div>';

        fetchSummary(id, controller.signal)
            .then(function (data) {
                panel.classList.remove('is-loading');
                if (data.error) {
                    content.innerHTML =
                        '<p style="padding:2rem;color:var(--cl-danger)">' +
                        escapeHtml(data.error) +
                        '</p>';
                    return;
                }
                cacheSet(id, data);
                showDetail(data, id, el);
            })
            .catch(function (err) {
                if (err.name === 'AbortError') return;
                panel.classList.remove('is-loading');
                content.innerHTML =
                    '<p style="padding:2rem;color:var(--cl-danger)">' +
                    escapeHtml(err.message || 'Failed to load analysis.') +
                    '</p>';
                content.classList.remove('is-swapping');
            })
            .finally(function () {
                if (loadingId === id) {
                    loadingId = null;
                }
            });
    };

    document.querySelectorAll('.history-item[data-id]').forEach(function (item) {
        item.addEventListener('mouseenter', function () {
            const id = parseInt(item.dataset.id, 10);
            if (cacheHas(id)) return;
            clearTimeout(prefetchTimer);
            prefetchTimer = setTimeout(function () {
                fetchSummary(id).then(function (data) {
                    cacheSet(id, data);
                }).catch(function () {});
            }, 200);
        });
    });

    window.deleteHistoryEntry = function (historyId, event, buttonEl) {
        if (event) {
            event.stopPropagation();
            event.preventDefault();
        }

        window.CodeLens.confirm({
            title: 'Delete Report',
            message: 'Are you sure you want to delete this report?',
            confirmText: 'Delete',
            cancelText: 'Cancel',
            variant: 'danger',
            onConfirm: function() {
                const itemEl = buttonEl ? buttonEl.closest('.history-item') : null;

                fetch('/api/history/' + historyId + '/delete/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrf(),
                        'Content-Type': 'application/json'
                    }
                })
                .then(function (r) {
                    if (!r.ok) throw new Error("Delete request failed");
                    return r.json();
                })
                .then(function (res) {
                    if (res.success) {
                        if (itemEl) {
                            // Fluid fade & collapse animation
                            itemEl.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                            itemEl.style.opacity = '0';
                            itemEl.style.transform = 'translateX(-20px)';
                            itemEl.style.maxHeight = '0px';
                            itemEl.style.paddingTop = '0px';
                            itemEl.style.paddingBottom = '0px';
                            itemEl.style.marginTop = '0px';
                            itemEl.style.marginBottom = '0px';
                            itemEl.style.border = 'none';

                            setTimeout(function () {
                                const wasActive = itemEl.classList.contains('is-active');
                                itemEl.remove();

                                // If deleted item was actively selected, clear details panel
                                if (wasActive) {
                                    content.innerHTML =
                                        '<div class="empty-state-premium" style="border:none;background:transparent;box-shadow:none">' +
                                        '<div class="empty-state-premium__icon"><i class="fa-solid fa-file-lines"></i></div>' +
                                        '<h3 style="font-family:var(--cl-font-display);margin-bottom:0.5rem">Select an analysis</h3>' +
                                        '<p style="color:var(--cl-text-muted)">Choose any entry from the reports on the left to instantly preview its results.</p>' +
                                        '<div class="beginner-tip">' +
                                        '<strong>💡 New here?</strong> Each analysis shows you:<br>' +
                                        '🐛 <strong>Errors</strong> — bugs found in your code<br>' +
                                        '🌿 <strong>Code Smells</strong> — bad habits to fix<br>' +
                                        '🤖 <strong>AI Refactor</strong> — a cleaned-up version<br>' +
                                        '❤️ <strong>Health Score</strong> — overall code quality' +
                                        '</div>' +
                                        '</div>';
                                }
                            }, 300);
                        } else {
                            window.location.reload();
                        }
                    } else {
                        alert("Failed to delete the report. Please try again.");
                    }
                })
                .catch(function (err) {
                    console.error(err);
                    alert("An error occurred while deleting the report.");
                });
            }
        });
    };
})();

