(function () {
    'use strict';

    var root = document.documentElement;
    var STORAGE = 'codelens-theme';

    function applyTheme(theme) {
        localStorage.setItem(STORAGE, theme);
        if (theme === 'system') {
            var isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            root.setAttribute('data-theme', isDark ? 'dark' : 'light');
        } else {
            root.setAttribute('data-theme', theme);
        }
        window.dispatchEvent(new CustomEvent('codelens-theme-change', { detail: { theme: theme } }));
    }

    // Observer for OS theme preferences changes
    try {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
            var current = localStorage.getItem(STORAGE) || 'system';
            if (current === 'system') {
                root.setAttribute('data-theme', e.matches ? 'dark' : 'light');
                window.dispatchEvent(new CustomEvent('codelens-theme-change', { detail: { theme: 'system' } }));
            }
        });
    } catch (err) {}

    window.CodeLens = {
        theme: function () { return localStorage.getItem(STORAGE) || 'system'; },
        setTheme: applyTheme,
        confirm: function(options) {
            var modal = document.getElementById('clGlobalModal');
            if (!modal) {
                if (window.confirm(options.message)) {
                    if (options.onConfirm) options.onConfirm();
                }
                return;
            }
            
            var titleEl = document.getElementById('clModalTitle');
            var msgEl = document.getElementById('clModalMessage');
            var confirmBtn = document.getElementById('clModalConfirm');
            var cancelBtn = document.getElementById('clModalCancel');
            var iconEl = document.getElementById('clModalIcon');
            
            if (titleEl) titleEl.textContent = options.title || 'Confirm Action';
            if (msgEl) msgEl.innerHTML = (options.message || 'Are you sure?').replace(/\n/g, '<br>');
            if (confirmBtn) confirmBtn.textContent = options.confirmText || 'Confirm';
            if (cancelBtn) cancelBtn.textContent = options.cancelText || 'Cancel';
            
            if (options.variant === 'danger') {
                if (confirmBtn) confirmBtn.className = 'cl-btn cl-btn--danger cl-btn--sm';
                if (iconEl) {
                    iconEl.className = 'fa-solid fa-triangle-exclamation';
                    iconEl.style.color = 'var(--cl-danger)';
                }
            } else if (options.variant === 'warning') {
                if (confirmBtn) confirmBtn.className = 'cl-btn cl-btn--warning cl-btn--sm';
                if (iconEl) {
                    iconEl.className = 'fa-solid fa-triangle-exclamation';
                    iconEl.style.color = 'var(--cl-warning)';
                }
            } else {
                if (confirmBtn) confirmBtn.className = 'cl-btn cl-btn--primary cl-btn--sm';
                if (iconEl) {
                    iconEl.className = 'fa-solid fa-circle-info';
                    iconEl.style.color = 'var(--cl-primary)';
                }
            }
            
            modal.style.display = 'flex';
            void modal.offsetWidth;
            modal.classList.add('is-visible');
            
            function closeModal() {
                modal.classList.remove('is-visible');
                setTimeout(function() { modal.style.display = 'none'; }, 250);
            }
            
            if (confirmBtn) confirmBtn.onclick = function() {
                closeModal();
                if (options.onConfirm) options.onConfirm();
            };
            if (cancelBtn) cancelBtn.onclick = closeModal;
        }
    };

    var sidebar = document.getElementById('sidebar');
    var sidebarToggle = document.getElementById('sidebarToggle');
    var sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
    var shell = document.querySelector('.cl-shell--app');

    if (sidebar && sidebarToggle) {
        sidebarToggle.addEventListener('click', function () {
            if (window.innerWidth <= 768) {
                sidebar.classList.toggle('is-open');
            } else if (shell) {
                shell.classList.toggle('sidebar-collapsed');
            }
        });

        if (sidebarCloseBtn) {
            sidebarCloseBtn.addEventListener('click', function () {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('is-open');
                } else if (shell) {
                    shell.classList.add('sidebar-collapsed');
                }
            });
        }

        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 768 && sidebar.classList.contains('is-open') && !sidebar.contains(e.target) && e.target !== sidebarToggle && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('is-open');
            }
        });
    }

    // User profile dropdown toggle
    var userDropdownBtn = document.getElementById('userDropdownBtn');
    var userDropdownMenu = document.getElementById('userDropdownMenu');
    if (userDropdownBtn && userDropdownMenu) {
        userDropdownBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            var isOpen = userDropdownMenu.classList.toggle('is-open');
            userDropdownBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            var caret = userDropdownBtn.querySelector('.cl-nav-user__caret');
            if (caret) {
                caret.style.transform = isOpen ? 'rotate(180deg)' : '';
            }
        });
        
        document.addEventListener('click', function (e) {
            if (!userDropdownMenu.contains(e.target) && !userDropdownBtn.contains(e.target)) {
                userDropdownMenu.classList.remove('is-open');
                userDropdownBtn.setAttribute('aria-expanded', 'false');
                var caret = userDropdownBtn.querySelector('.cl-nav-user__caret');
                if (caret) {
                    caret.style.transform = '';
                }
            }
        });
    }

    var reveals = document.querySelectorAll('[data-reveal]');
    if (reveals.length && 'IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-revealed');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });
        reveals.forEach(function (el) { io.observe(el); });
    } else {
        reveals.forEach(function (el) { el.classList.add('is-revealed'); });
    }
})();
