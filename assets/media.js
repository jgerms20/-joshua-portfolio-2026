/* =====================================================
   Shared media layer.

   Images:  <img src="a.jpg" data-fallbacks="yt:VIDEOID b.jpg">
            Tries src, then each fallback in order. "yt:ID" expands to
            YouTube's maxres -> sd -> hq thumbnails. When every source
            fails, the image's container becomes a labelled ink tile
            (or collapses, for decorative gallery figures) instead of an
            empty box.

   Films:   <div class="film-frame mv-frame" data-yt="ID" data-title="…">
            <div class="film-frame mv-frame" data-ispot="ID" data-poster="x.jpg" data-title="…">
            <div class="film-frame mv-frame" data-mp4="x.mp4" data-poster="x.jpg" data-title="…">
            Renders a poster + play button. The player only loads on
            click, and a "Watch on …" link always sits underneath so a
            blocked or pulled embed never leaves a dead box.
   ===================================================== */
(function () {
    'use strict';

    var YT_PLACEHOLDER_MAX = 120; // YouTube serves a 120x90 grey tile for missing sizes

    function expand(tok) {
        if (tok.indexOf('yt:') === 0) {
            var id = tok.slice(3);
            return [
                'https://i.ytimg.com/vi/' + id + '/maxresdefault.jpg',
                'https://i.ytimg.com/vi/' + id + '/sddefault.jpg',
                'https://i.ytimg.com/vi/' + id + '/hqdefault.jpg'
            ];
        }
        return [tok];
    }

    function queueFor(img) {
        var list = [];
        (img.getAttribute('data-fallbacks') || '').split(/\s+/).forEach(function (t) {
            if (t) list = list.concat(expand(t));
        });
        return list;
    }

    function markLetterbox(img) {
        var s = img.currentSrc || img.src || '';
        img.classList.toggle('mv-letterbox', /\/(sd|hq)default\.jpg/.test(s));
    }

    function giveUp(img) {
        var film = img.closest('.mv-film');
        if (film) { film.classList.add('mv-noposter'); return; }
        var fig = img.closest('[data-mv-collapse], figure.fig');
        if (fig) { fig.classList.add('mv-collapse'); return; }
        var box = img.closest('.plate-media, .mv-box, .shop-card-media, .lab-art, .site-shot');
        if (!box) { img.style.visibility = 'hidden'; return; }
        box.classList.add('mv-empty');
        box.setAttribute('data-mv-label', img.getAttribute('data-label') || img.getAttribute('alt') || '');
    }

    function advance(img) {
        if (!img._mvQueue) img._mvQueue = queueFor(img);
        var next = img._mvQueue.shift();
        if (next) { img.src = next; } else { giveUp(img); }
    }

    function guard(img) {
        if (img._mvGuarded) return;
        img._mvGuarded = true;
        img.addEventListener('error', function () { advance(img); });
        img.addEventListener('load', function () {
            var ytTile = /i\.ytimg\.com|img\.youtube\.com/.test(img.src) && img.naturalWidth <= YT_PLACEHOLDER_MAX;
            if (ytTile) { advance(img); return; }
            markLetterbox(img);
        });
        // Already settled before this script ran?
        if (img.complete) {
            if (img.naturalWidth === 0 && img.getAttribute('src')) advance(img);
            else markLetterbox(img);
        } else if (!img.getAttribute('src') && img.hasAttribute('data-fallbacks')) {
            advance(img);
        }
    }

    var ICON = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><polygon points="6,3 21,12 6,21"/></svg>';

    function esc(s) {
        return String(s || '').replace(/[&<>"]/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
        });
    }

    function hydrateFilm(frame) {
        if (frame._mvDone) return;
        frame._mvDone = true;
        var yt = frame.getAttribute('data-yt');
        var ispot = frame.getAttribute('data-ispot');
        var mp4 = frame.getAttribute('data-mp4');
        var title = frame.getAttribute('data-title') || 'Watch the film';
        var poster = frame.getAttribute('data-poster') || '';
        var src, fallbacks, outHref, outLabel;

        if (yt) {
            src = poster || 'https://i.ytimg.com/vi/' + yt + '/maxresdefault.jpg';
            fallbacks = (poster ? 'yt:' + yt : 'https://i.ytimg.com/vi/' + yt + '/sddefault.jpg https://i.ytimg.com/vi/' + yt + '/hqdefault.jpg');
            outHref = 'https://www.youtube.com/watch?v=' + yt;
            outLabel = 'YouTube';
        } else if (ispot) {
            src = poster; fallbacks = '';
            outHref = 'https://www.ispot.tv/ad/' + ispot;
            outLabel = 'iSpot';
        } else if (mp4) {
            src = poster; fallbacks = '';
            outHref = mp4;
            outLabel = 'Film';
        } else {
            return;
        }

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'mv-film' + (src ? '' : ' mv-noposter');
        btn.setAttribute('aria-label', 'Play: ' + title);
        btn.innerHTML =
            (src ? '<img class="mv-poster" alt="" loading="lazy" decoding="async" src="' + esc(src) + '"' +
                   (fallbacks ? ' data-fallbacks="' + esc(fallbacks) + '"' : '') + '>' : '') +
            '<span class="mv-play">' + ICON + '</span>' +
            '<span class="mv-cap"><span class="mv-cap-title">' + esc(title) + '</span>' +
            '<span class="mv-cap-src">' + (outLabel === 'Film' ? '▶ Play' : '▶ ' + outLabel) + '</span></span>';
        frame.innerHTML = '';
        frame.appendChild(btn);
        var img = btn.querySelector('img');
        if (img) guard(img);

        btn.addEventListener('click', function () {
            var el;
            if (yt) {
                el = document.createElement('iframe');
                el.src = 'https://www.youtube-nocookie.com/embed/' + yt + '?autoplay=1&rel=0&modestbranding=1&playsinline=1';
                el.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen';
                el.allowFullscreen = true;
            } else if (ispot) {
                el = document.createElement('iframe');
                el.src = 'https://www.ispot.tv/share/' + ispot;
                el.allow = 'autoplay; fullscreen; picture-in-picture';
                el.allowFullscreen = true;
            } else {
                el = document.createElement('video');
                el.src = mp4; el.controls = true; el.autoplay = true; el.playsInline = true;
                if (poster) el.poster = poster;
            }
            el.className = 'mv-frame-live';
            el.title = title;
            frame.innerHTML = '';
            frame.appendChild(el);
            if (el.focus) el.focus();
        });

        // Escape hatch under every film, unless the page already has one.
        var holder = frame.parentElement;
        if (holder && !holder.querySelector('.mv-out') && outLabel !== 'Film') {
            var a = document.createElement('a');
            a.className = 'mv-out';
            a.href = outHref; a.target = '_blank'; a.rel = 'noopener';
            a.textContent = 'Watch on ' + outLabel + ' ↗';
            frame.insertAdjacentElement('afterend', a);
        }
    }

    function init(root) {
        root = root || document;
        root.querySelectorAll('.mv-frame[data-yt], .mv-frame[data-ispot], .mv-frame[data-mp4]').forEach(hydrateFilm);
        root.querySelectorAll('img').forEach(function (img) {
            if (img.closest('.mv-film') && img._mvGuarded) return;
            guard(img);
        });
    }

    window.MV = { init: init, guard: guard };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { init(); });
    else init();
})();
