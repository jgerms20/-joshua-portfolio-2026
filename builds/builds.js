// Shared behaviour for builds/*.html: theme toggle, hide-on-scroll nav, reveal on scroll.
(function () {
    var btn = document.getElementById('themeToggle');
    if (btn) {
        btn.addEventListener('click', function () {
            var root = document.documentElement;
            var dark = root.getAttribute('data-theme') === 'dark';
            if (dark) { root.removeAttribute('data-theme'); }
            else { root.setAttribute('data-theme', 'dark'); }
            try { localStorage.setItem('jmg-theme', dark ? 'light' : 'dark'); } catch (e) {}
        });
    }

    var nav = document.getElementById('nav');
    if (nav) {
        var lastY = 0;
        window.addEventListener('scroll', function () {
            var y = window.scrollY;
            if (y > 300 && y > lastY) nav.classList.add('hidden-up');
            else nav.classList.remove('hidden-up');
            lastY = y;
        }, { passive: true });
    }

    var items = document.querySelectorAll('.rv');
    if (!('IntersectionObserver' in window)) {
        items.forEach(function (el) { el.classList.add('in'); });
        return;
    }
    var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
            if (e.isIntersecting) { e.target.classList.add('in'); obs.unobserve(e.target); }
        });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
    items.forEach(function (el) { obs.observe(el); });
})();
