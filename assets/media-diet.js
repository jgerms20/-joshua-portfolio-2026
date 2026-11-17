/* =====================================================
   Media Diet: the shelf, as a component.

   <div class="md-app" data-root="./" data-hash-prefix="md-" data-per-page="12"></div>

   data-root           Path from the page to the site root. The shelf fetches
                       data/media-diet.json (Letterboxd + Goodreads, synced),
                       data/watching.json (TV, hand-edited), data/listening.json
                       (hand-edited picks) and data/spotify.json (saved albums,
                       shows and episodes, synced) from there. Any of them can be
                       missing or empty.
                       "./" on the homepage, "../" on /media-diet/.
   data-hash-prefix    Deep links. "md-" gives #md-watching / #md-reading /
                       #md-listening and never touches any other hash on the page.
                       "" means the page owns the hash (#reading). Leave the
                       attribute off for no hash routing at all.
   data-per-page       Cards per page (default 24).
   data-pager          "compact": Prev · Page 2 of 5 · Next, no page numbers.
   data-heading-level  Heading level for empty-state titles (default 3).
   data-doc-title      Retitle the browser tab per shelf: "Reading · <this>".
   data-stack          Optional selector: fan the newest three covers into it.
   data-synced         Optional selector: write "Synced Nov 3, 2026" into it.

   Rules: every piece of data goes in through textContent, links and
   images are https-only, a missing or broken image becomes a designed
   tile, and an empty shelf links out to where the full log lives.
   ===================================================== */
(function () {
    'use strict';

    var HAS_DOM = typeof window !== 'undefined' && typeof document !== 'undefined' &&
        !!(window.fetch && window.Promise && document.querySelectorAll);

    var LETTERBOXD = 'https://letterboxd.com/jgerms/';
    var GOODREADS = 'https://www.goodreads.com/user/show/95365432-joshua-german';
    var SVG = 'http://www.w3.org/2000/svg';
    var ICON = {
        out: 'M7 17 17 7M8 7h9v9',
        search: 'M18 11a7 7 0 1 1-14 0 7 7 0 0 1 14 0zM20 20l-3.5-3.5',
        prev: 'M15 18l-6-6 6-6',
        next: 'M9 18l6-6-6-6',
        rewatch: 'M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.2L3 16M3 21v-5h5'
    };

    // ---- Helpers: data only ever reaches the page as text ----
    function el(tag, cls, text) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text != null && text !== '') n.textContent = String(text);
        return n;
    }
    function https(u) { return (typeof u === 'string' && /^https:\/\/[^\s"'<>]+$/.test(u.trim())) ? u.trim() : ''; }
    function str(v, max) { return typeof v === 'string' ? v.trim().slice(0, max || 200) : (typeof v === 'number' ? String(v) : ''); }
    // YYYY-MM-DD, or YYYY-MM when only the month is known (shown as "Aug 2013")
    function isoDate(v) {
        if (typeof v !== 'string') return '';
        if (/^\d{4}-\d{2}-\d{2}/.test(v)) return v.slice(0, 10);
        return /^\d{4}-\d{2}$/.test(v) ? v : '';
    }
    function fmtDate(d, withYear) {
        if (!d) return '';
        if (d.length === 7) {
            var m = new Date(d + '-01T00:00:00Z');
            return isNaN(m) ? '' : m.toLocaleDateString('en-US', { month: 'short', year: 'numeric', timeZone: 'UTC' });
        }
        var x = new Date(d + 'T00:00:00Z');
        if (isNaN(x)) return '';
        return x.toLocaleDateString('en-US', withYear === false
            ? { month: 'short', day: 'numeric', timeZone: 'UTC' }
            : { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
    }
    function num(v, max) { var n = typeof v === 'number' ? v : parseFloat(v); return (isFinite(n) && n > 0 && n <= max) ? n : null; }
    function stars(r) { return r ? '★'.repeat(Math.floor(r)) + (r % 1 ? '½' : '') : ''; }
    function plural(n, one, many) { return n + ' ' + (n === 1 ? one : many); }
    function sortTitle(t) { return t.toLowerCase().replace(/^(the|a|an)\s+/, ''); }
    function icon(d, width) {
        var s = document.createElementNS(SVG, 'svg');
        s.setAttribute('viewBox', '0 0 24 24'); s.setAttribute('fill', 'none'); s.setAttribute('stroke', 'currentColor');
        s.setAttribute('stroke-width', width || '2'); s.setAttribute('stroke-linecap', 'round'); s.setAttribute('stroke-linejoin', 'round');
        s.setAttribute('aria-hidden', 'true'); s.setAttribute('focusable', 'false');
        var p = document.createElementNS(SVG, 'path');
        p.setAttribute('d', d);
        s.appendChild(p);
        return s;
    }
    function link(url, cls) {
        var a = el(url ? 'a' : 'div', cls);
        if (url) { a.href = url; a.target = '_blank'; a.rel = 'noopener'; }
        return a;
    }
    function opensNewTab(a) { a.appendChild(el('span', 'md-sr', ' (opens in a new tab)')); return a; }
    // Image with a typographic fallback: no image, or a broken one, becomes a designed tile
    function cover(src, makeTile) {
        var box = el('span', 'md-cover');
        var url = https(src);
        if (url) {
            var img = el('img');
            img.alt = ''; img.loading = 'lazy'; img.decoding = 'async'; img.referrerPolicy = 'no-referrer';
            img.addEventListener('error', function () { img.replaceWith(makeTile()); });
            img.src = url;
            box.appendChild(img);
        } else box.appendChild(makeTile());
        return box;
    }
    function tile(kind, title, k) {
        return function () {
            var t = el('span', 'md-tile md-tile--' + kind);
            t.appendChild(el('span', 'md-tile-t', title));
            if (k) t.appendChild(el('span', 'md-tile-k', k));
            return t;
        };
    }

    // ---- Normalise the two data files into one item shape per shelf ----
    var TYPES = {
        podcast: ['Podcast', 'Podcasts'], episode: ['Episode', 'Episodes'], article: ['Article', 'Articles'],
        album: ['Album', 'Albums'], song: ['Song', 'Songs'], video: ['Video', 'Videos']
    };
    function films(data) {
        return (Array.isArray(data && data.letterboxd) ? data.letterboxd : []).filter(function (f) { return f && str(f.title); }).map(function (f) {
            var year = /^\d{4}$/.test(str(f.year)) ? str(f.year) : '';
            return {
                kind: 'film', group: 'film', title: str(f.title, 160), year: year, decade: year ? year.slice(0, 3) + '0s' : '',
                rating: num(f.rating, 5), date: isoDate(f.watched), rewatch: f.rewatch === true,
                image: https(f.poster), url: https(f.url)
            };
        });
    }
    function books(data) {
        var list = [], seen = {};
        function add(b, now) {
            if (!b || !str(b.title)) return;
            var key = https(b.url) || str(b.title);
            if (seen[key]) return;
            seen[key] = 1;
            list.push({
                kind: 'book', group: 'book', title: str(b.title, 160), author: str(b.author, 100), rating: num(b.rating, 5),
                date: isoDate(b.date), now: now, image: https(b.cover), url: https(b.url)
            });
        }
        (Array.isArray(data && data.reading) ? data.reading : []).forEach(function (b) { add(b, true); });
        (Array.isArray(data && data.read) ? data.read : []).forEach(function (b) { add(b, false); });
        return list;
    }
    // TV is logged by hand in data/watching.json and sits with the films
    function tv(data) {
        return (Array.isArray(data && data.items) ? data.items : []).filter(function (x) {
            return x && str(x.type).toLowerCase() === 'tv' && str(x.title);
        }).map(function (x) {
            var season = str(x.season, 40);
            return {
                kind: 'tv', group: 'tv', title: str(x.title, 160), season: /^\d+$/.test(season) ? 'Season ' + season : season,
                year: '', decade: '', rating: null, date: isoDate(x.date), rewatch: false,
                image: https(x.image), url: https(x.url), note: str(x.note, 220)
            };
        });
    }
    // Episodes and shows are both "Podcasts" when the shelf is filtered or counted
    function listenGroup(type) { return type === 'episode' ? 'podcast' : type; }
    function listening(data) {
        return (Array.isArray(data && data.items) ? data.items : []).filter(function (x) { return x && str(x.title); }).map(function (x) {
            var type = TYPES.hasOwnProperty(str(x.type).toLowerCase()) ? str(x.type).toLowerCase() : 'article';
            return {
                kind: 'listen', type: type, group: listenGroup(type), title: str(x.title, 160), creator: str(x.creator, 100), note: str(x.note, 220),
                date: isoDate(x.date), image: https(x.image), url: https(x.url)
            };
        });
    }
    // data/spotify.json (scripts/sync-spotify.py): saved albums, shows and episodes
    function spotify(data) {
        var out = [];
        function add(list, type, by) {
            (Array.isArray(list) ? list : []).forEach(function (x) {
                if (!x || !str(x.title)) return;
                out.push({
                    kind: 'listen', type: type, group: listenGroup(type), title: str(x.title, 160), creator: str(x[by], 100), note: '',
                    date: isoDate(x.added), image: https(x.image), url: https(x.url)
                });
            });
        }
        add(data && data.albums, 'album', 'artist');
        add(data && data.shows, 'podcast', 'publisher');
        add(data && data.episodes, 'episode', 'show');
        return out;
    }
    // Hand picks first (they carry the notes), then anything Spotify adds; one card per link
    function dedupe(list) {
        var seen = {};
        return list.filter(function (it) {
            var key = it.url ? it.url.split(/[?#]/)[0].replace(/\/$/, '') : '';
            if (!key) return true;
            if (seen[key]) return false;
            seen[key] = 1;
            return true;
        });
    }
    function buildShelves(diet, listen, watch, spot) {
        var picks = listening(listen);
        return {
            watching: films(diet).concat(tv(watch)),
            reading: books(diet).concat(picks.filter(function (i) { return i.type === 'article'; })),
            listening: dedupe(picks.filter(function (i) { return i.type !== 'article'; }).concat(spotify(spot))),
            updated: isoDate(diet && diet.updated)
        };
    }

    // ---- "Latest + how often": one line per shelf, worked out from the dates in the data ----
    var SUMMARY = {
        watching: { days: 30, when: true, groups: [['film', 'film', 'films'], ['tv', 'show', 'shows']] },
        reading: { days: 90, groups: [['book', 'book', 'books'], ['article', 'article', 'articles']] },
        listening: { days: 90, groups: [['album', 'album', 'albums'], ['podcast', 'podcast', 'podcasts']] }
    };
    function dayNumber(d) {
        var m = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(d || '');
        return m ? Date.UTC(+m[1], +m[2] - 1, m[3] ? +m[3] : 1) / 864e5 : NaN;
    }
    function todayISO() {
        var n = new Date();
        return n.getFullYear() + '-' + ('0' + (n.getMonth() + 1)).slice(-2) + '-' + ('0' + n.getDate()).slice(-2);
    }
    // summaryLine('watching', items, '2026-11-17') -> "Latest: Sinners, Nov 12 · 4 films in the last 30 days"
    // No dates, no line. Nothing in the window, no count. Never a zero.
    function summaryLine(key, list, today) {
        var def = SUMMARY[key], now = dayNumber(today);
        if (!def || !Array.isArray(list) || isNaN(now)) return '';
        var latest = null;
        list.forEach(function (it) {
            // a day of slack for time zones; anything dated further ahead is not "latest" yet
            if (!it || !it.date || !(dayNumber(it.date) <= now + 1)) return;
            if (!latest || it.date.localeCompare(latest.date) > 0) latest = it;
        });
        if (!latest) return '';
        var out = 'Latest: ' + latest.title;
        if (def.when) {
            var when = fmtDate(latest.date, latest.date.slice(0, 4) !== today.slice(0, 4));
            if (when) out += ', ' + when;
        }
        var counts = [];
        def.groups.forEach(function (g) {
            var n = list.filter(function (it) {
                var age = it && it.date ? now - dayNumber(it.date) : NaN;
                return it.group === g[0] && age >= -1 && age <= def.days;
            }).length;
            if (n) counts.push(plural(n, g[1], g[2]));
        });
        if (counts.length) out += ' · ' + counts.join(' and ') + ' in the last ' + def.days + ' days';
        return out;
    }

    // ---- Shelves ----
    var SHELVES = {
        watching: {
            name: 'Watching', dek: 'Every film I log, with the stars to prove it.', source: 'Letterboxd', href: LETTERBOXD,
            noun: function (items) { return hasTV(items) ? ['title', 'titles'] : ['film', 'films']; },
            search: function (items) { return hasTV(items) ? 'Search films, shows or years' : 'Search films or years'; },
            chips: function () { return [['all', 'All'], ['films', 'Films', 1], ['tv', 'TV', 1], ['first', 'First watch'], ['rewatch', 'Rewatches']]; },
            chip: function (it, c) {
                if (c === 'all') return true;
                if (c === 'films') return it.kind === 'film';
                if (c === 'tv') return it.kind === 'tv';
                return it.kind === 'film' && (c === 'rewatch' ? it.rewatch : !it.rewatch);
            },
            count: function (n, items) { return n ? (hasTV(items) ? n + ' logged' : plural(n, 'film logged', 'films logged')) : 'Soon'; },
            empty: {
                title: ['The reel is ', 'rewinding.'],
                text: 'Every film I log lands here with its stars. Until the next sync, the full diary lives on Letterboxd.',
                cta: ['See my Letterboxd diary', LETTERBOXD]
            }
        },
        reading: {
            name: 'Reading', dek: 'Books on the nightstand and articles worth passing on.', source: 'Goodreads', href: GOODREADS,
            noun: ['read', 'reads'], search: 'Search titles, authors, publications',
            chips: function () { return [['all', 'All'], ['books', 'Books', 1], ['articles', 'Articles', 1], ['now', 'Now reading']]; },
            chip: function (it, c) { return c === 'all' || (c === 'articles' ? it.kind === 'listen' : c === 'books' ? it.kind === 'book' : !!it.now); },
            count: function (n) { return n ? plural(n, 'read', 'reads') : 'On Goodreads'; },
            empty: {
                title: ['The nightstand is ', 'on Goodreads.'],
                text: 'What I’m reading now and every book I’ve finished, with ratings. The shelf here fills itself in from there.',
                cta: ['See my Goodreads shelves', GOODREADS]
            }
        },
        listening: {
            name: 'Listening', dek: 'Podcasts and episodes I keep bringing up, picked by hand.', source: '', href: '',
            noun: ['pick', 'picks'], search: 'Search titles, hosts, authors',
            chips: function () { return [['all', 'All'], ['album', 'Albums', 1], ['podcast', 'Podcasts', 1], ['song', 'Songs', 1], ['video', 'Videos', 1]]; },
            chip: function (it, c) { return c === 'all' || it.group === c; },
            count: function (n) { return n ? plural(n, 'pick', 'picks') : 'Coming soon'; },
            empty: {
                round: true,
                title: ['In my ears — ', 'coming soon.'],
                text: 'Podcasts and episodes I’m into, picked by hand. The first few are on their way.'
            }
        }
    };
    var ORDER = ['watching', 'reading', 'listening'];
    function hasTV(items) { return items.some(function (i) { return i.kind === 'tv'; }); }
    // The chips a shelf shows: [id, label, count]. A chip with nothing behind it is left out,
    // and so is a type chip that would only repeat "All" (a shelf holding one type).
    function chipList(key, list) {
        var shelf = SHELVES[key], out = [];
        shelf.chips(list).forEach(function (d) {
            var count = list.filter(function (i) { return shelf.chip(i, d[0]); }).length;
            if (d[0] !== 'all' && (!count || (d[2] && count === list.length))) return;
            out.push([d[0], d[1], count]);
        });
        return out;
    }
    var FILTERED = {
        title: ['Nothing on this shelf ', 'matches.'],
        text: 'Try a different search, or clear the filters to see everything.',
        clear: true
    };

    // ---- Filtering + sorting ----
    function matches(it, st, shelf) {
        if (!shelf.chip(it, st.chip)) return false;
        if (st.rating !== 'any') {
            if (st.rating === 'unrated') { if (it.rating) return false; }
            else if (st.rating === 'under3') { if (!it.rating || it.rating >= 3) return false; }
            else if (!it.rating || it.rating < parseFloat(st.rating)) return false;
        }
        if (st.decade !== 'any' && it.decade !== st.decade) return false;
        if (st.q) {
            var hay = [it.title, it.year, it.author, it.creator, it.note, it.season, it.kind === 'tv' && 'TV', it.type && TYPES[it.type][0]].join(' ').toLowerCase();
            var words = st.q.toLowerCase().split(/\s+/).filter(Boolean);
            for (var i = 0; i < words.length; i++) if (hay.indexOf(words[i]) === -1) return false;
        }
        return true;
    }
    function byDate(a, b) { return (b.date || '').localeCompare(a.date || ''); }
    function sorted(list, st, key) {
        var out = list.slice();
        var cmp = {
            'new': byDate,
            'old': function (a, b) { return (a.date || '9999').localeCompare(b.date || '9999'); },
            'rated': function (a, b) { return (b.rating || 0) - (a.rating || 0) || byDate(a, b); },
            'title': function (a, b) { return sortTitle(a.title).localeCompare(sortTitle(b.title)); },
            'release': function (a, b) { return (b.year || '0').localeCompare(a.year || '0') || byDate(a, b); }
        }[st.sort] || byDate;
        out.sort(cmp);
        // On the default sort, what's on the nightstand comes first
        if (key === 'reading' && st.sort === 'new') out.sort(function (a, b) { return (b.now ? 1 : 0) - (a.now ? 1 : 0); });
        return out;
    }

    // ---- Cards ----
    function filmCard(f) {
        var a = link(f.url, 'md-card md-card--film');
        a.setAttribute('aria-label', f.title + (f.year ? ' (' + f.year + ')' : '') + (f.rating ? ', rated ' + f.rating + ' out of 5' : '') + (f.rewatch ? ', rewatch' : ''));
        a.appendChild(cover(f.image, tile('film', f.title, f.year)));
        var meta = el('span', 'md-card-meta');
        meta.appendChild(el('span', 'md-stars', stars(f.rating)));
        if (f.rewatch) {
            var rw = el('span', 'md-rw');
            rw.appendChild(icon(ICON.rewatch));
            rw.appendChild(el('span', null, 'Rewatch'));
            meta.appendChild(rw);
        }
        a.appendChild(meta);
        a.appendChild(el('span', 'md-name', f.title));
        var when = el('span', 'md-when', f.year);
        if (f.date) {
            if (f.year) when.appendChild(document.createTextNode(' · '));
            when.appendChild(el('span', 'md-wv', 'Watched '));
            when.appendChild(document.createTextNode(fmtDate(f.date, false) + ' ’' + f.date.slice(2, 4)));
        }
        a.appendChild(when);
        return a;
    }
    // A season of TV: same poster card as a film, labelled so nobody takes it for one
    function tvCard(t) {
        var a = link(t.url, 'md-card md-card--film md-card--tv');
        a.setAttribute('aria-label', 'TV: ' + t.title + (t.season ? ', ' + t.season : ''));
        a.appendChild(cover(t.image, tile('film', t.title, 'TV')));
        var meta = el('span', 'md-card-meta');
        meta.appendChild(el('span', 'md-tv', 'TV'));
        a.appendChild(meta);
        a.appendChild(el('span', 'md-name', t.title));
        var when = el('span', 'md-when', t.season);
        if (t.date) {
            if (t.season) when.appendChild(document.createTextNode(' · '));
            when.appendChild(el('span', 'md-wv', 'Watched '));
            when.appendChild(document.createTextNode(t.date.length === 7 ? fmtDate(t.date) : fmtDate(t.date, false) + ' ’' + t.date.slice(2, 4)));
        }
        if (t.season || t.date) a.appendChild(when);
        if (t.note) a.appendChild(el('span', 'md-by', t.note));
        return a;
    }
    function bookCard(b) {
        var a = link(b.url, 'md-card md-card--book');
        a.setAttribute('aria-label', b.title + (b.author ? ' by ' + b.author : '') + (b.now ? ', reading now' : '') + (b.rating ? ', rated ' + b.rating + ' out of 5' : ''));
        var c = cover(b.image, tile('book', b.title, b.author));
        if (b.now) c.appendChild(el('span', 'md-badge md-badge--now', 'Now reading'));
        a.appendChild(c);
        var meta = el('span', 'md-card-meta');
        meta.appendChild(el('span', 'md-stars', stars(b.rating)));
        a.appendChild(meta);
        a.appendChild(el('span', 'md-name', b.title));
        if (b.author) a.appendChild(el('span', 'md-by', b.author));
        if (b.date) a.appendChild(el('span', 'md-when', (b.now ? 'Started ' : '') + fmtDate(b.date)));
        return a;
    }
    function listenCard(x) {
        var a = link(x.url, 'md-card md-card--listen');
        a.dataset.type = x.type;
        a.setAttribute('aria-label', TYPES[x.type][0] + ': ' + x.title + (x.creator ? ', ' + x.creator : ''));
        // The tile names the show or publication: "Author · Publication" shows the publication
        var label = x.creator ? x.creator.split(' · ').pop() : x.title;
        a.appendChild(cover(x.image, function () {
            var t = el('span', 'md-tile md-tile--listen');
            t.appendChild(el('span', 'md-tile-t', label));
            return t;
        }));
        var body = el('span');
        var top = el('span', 'md-card-meta');
        top.appendChild(el('span', 'md-type', TYPES[x.type][0]));
        if (x.date) top.appendChild(el('span', 'md-when', fmtDate(x.date)));
        body.appendChild(top);
        body.appendChild(el('span', 'md-name', x.title));
        if (x.creator) body.appendChild(el('span', 'md-by', x.creator));
        if (x.note) body.appendChild(el('span', 'md-note', x.note));
        a.appendChild(body);
        return a;
    }
    // Articles sit on the Reading shelf next to the books: same card shape, the publication on the cover
    function articleCard(x) {
        var a = link(x.url, 'md-card md-card--book md-card--article');
        a.setAttribute('aria-label', 'Article: ' + x.title + (x.creator ? ', ' + x.creator : ''));
        var parts = x.creator ? x.creator.split(' · ') : [];
        var c = cover(x.image, tile('book', parts.length ? parts[parts.length - 1] : x.title, 'Article'));
        a.appendChild(c);
        a.appendChild(el('span', 'md-name', x.title));
        if (x.creator) a.appendChild(el('span', 'md-by', x.creator));
        if (x.date) a.appendChild(el('span', 'md-when', fmtDate(x.date)));
        return a;
    }
    var CARD = { watching: function (it) { return it.kind === 'tv' ? tvCard(it) : filmCard(it); }, reading: function (it) { return it.kind === 'listen' ? articleCard(it) : bookCard(it); }, listening: listenCard };

    // ---- Empty states: static copy, built as text ----
    function emptyState(def, heading) {
        var box = el('div', 'md-empty');
        var art = el('div', 'md-empty-art' + (def.round ? ' is-round' : ''));
        art.setAttribute('aria-hidden', 'true');
        for (var i = 0; i < 3; i++) art.appendChild(el('span'));
        box.appendChild(art);
        var body = el('div');
        var h = el(heading, 'md-empty-title', def.title[0]);
        h.appendChild(el('em', null, def.title[1]));
        body.appendChild(h);
        body.appendChild(el('p', 'md-empty-text', def.text));
        if (def.cta) {
            var a = link(def.cta[1], 'md-btn');
            a.appendChild(document.createTextNode(def.cta[0] + ' '));
            a.appendChild(icon(ICON.out, '2.2'));
            body.appendChild(opensNewTab(a));
        }
        if (def.clear) {
            var b = el('button', 'md-btn', 'Clear filters');
            b.type = 'button';
            b.setAttribute('data-clear', '');
            body.appendChild(b);
        }
        box.appendChild(body);
        return box;
    }

    // ---- Pager: prev, 1 … 4 5 6 … 12, next ----
    function pageList(page, pages) {
        var out = [];
        for (var p = 1; p <= pages; p++) {
            if (p === 1 || p === pages || Math.abs(p - page) <= 1 || (page <= 3 && p <= 4) || (page >= pages - 2 && p >= pages - 3)) out.push(p);
            else if (out[out.length - 1] !== '…') out.push('…');
        }
        return out;
    }
    function stepBtn(dir, disabled, page) {
        var b = el('button', 'md-pg md-pg--step');
        b.type = 'button';
        b.disabled = disabled;
        b.dataset.page = String(page);
        b.dataset.dir = dir < 0 ? 'prev' : 'next';
        var label = el('span', null, dir < 0 ? 'Prev' : 'Next');
        var arrow = icon(dir < 0 ? ICON.prev : ICON.next);
        if (dir < 0) { b.appendChild(arrow); b.appendChild(label); } else { b.appendChild(label); b.appendChild(arrow); }
        b.setAttribute('aria-label', (dir < 0 ? 'Previous' : 'Next') + ' page');
        return b;
    }

    // ---- Fetch once per site root, however many shelves mount ----
    var loads = {};
    function getJSON(url) {
        return fetch(url, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    }
    function load(root) {
        if (!loads[root]) {
            loads[root] = Promise.all([
                getJSON(root + 'data/media-diet.json'), getJSON(root + 'data/listening.json'),
                getJSON(root + 'data/watching.json'), getJSON(root + 'data/spotify.json')
            ]).then(function (res) {
                return buildShelves(res[0] || {}, res[1] || {}, res[2] || {}, res[3] || {});
            }).catch(function () { return { watching: [], reading: [], listening: [], updated: '' }; });
        }
        return loads[root];
    }
    // Only plain relative (or root-absolute) prefixes: '', './', '../', '../../', '/'
    function safeRoot(v) {
        v = typeof v === 'string' ? v.trim() : '';
        if (v && v.slice(-1) !== '/') v += '/';
        return /^(\/|(\.\.?\/)+)?$/.test(v) ? v : '';
    }
    function find(sel) {
        if (!sel) return null;
        try { return document.querySelector(sel); } catch (e) { return null; }
    }
    function jumpTo(node) {
        try { node.scrollIntoView({ block: 'start', behavior: 'instant' }); } catch (e) { node.scrollIntoView(true); }
    }

    // =====================================================
    // Mount one shelf
    // =====================================================
    function mount(app, n) {
        if (app.getAttribute('data-md-mounted')) return;
        app.setAttribute('data-md-mounted', 'true');

        var prefixAttr = app.getAttribute('data-hash-prefix');
        var opt = {
            root: safeRoot(app.getAttribute('data-root')),
            prefix: prefixAttr === null ? null : prefixAttr.replace(/[^A-Za-z0-9_-]/g, ''),
            perPage: Math.min(Math.max(parseInt(app.getAttribute('data-per-page'), 10) || 24, 1), 96),
            compact: app.getAttribute('data-pager') === 'compact',
            heading: /^[2-6]$/.test(app.getAttribute('data-heading-level') || '') ? 'h' + app.getAttribute('data-heading-level') : 'h3',
            docTitle: str(app.getAttribute('data-doc-title'), 120),
            stack: find(app.getAttribute('data-stack')),
            synced: find(app.getAttribute('data-synced'))
        };
        var uid = 'md' + (n + 1);

        var items = { watching: [], reading: [], listening: [] };
        var state = {};
        ORDER.forEach(function (k) { state[k] = { q: '', chip: 'all', rating: 'any', decade: 'any', sort: 'new', page: 1 }; });
        var current = ORDER[0];
        var loaded = false;

        // ---- Build the frame (replaces any <noscript> fallback inside the mount) ----
        app.textContent = '';
        var tabs = el('div', 'md-tabs');
        tabs.setAttribute('role', 'tablist');
        tabs.setAttribute('aria-label', 'Media diet shelves');
        var tabEl = {}, countEl = {};
        ORDER.forEach(function (k, i) {
            var b = el('button', 'md-tab');
            b.type = 'button';
            b.id = uid + '-tab-' + k;
            b.dataset.tab = k;
            b.setAttribute('role', 'tab');
            b.setAttribute('aria-controls', uid + '-panel');
            b.setAttribute('aria-selected', 'false');
            b.tabIndex = -1;
            var numEl = el('span', 'md-tab-num', '0' + (i + 1));
            numEl.setAttribute('aria-hidden', 'true');
            b.appendChild(numEl);
            b.appendChild(el('span', 'md-tab-name', SHELVES[k].name));
            countEl[k] = b.appendChild(el('span', 'md-tab-count'));
            tabEl[k] = tabs.appendChild(b);
        });

        var panel = el('div', 'md-panel');
        panel.id = uid + '-panel';
        panel.setAttribute('role', 'tabpanel');
        panel.tabIndex = -1;

        var head = el('div', 'md-panel-head');
        var lede = head.appendChild(el('div', 'md-lede'));
        var dek = lede.appendChild(el('p', 'md-dek'));
        var latest = lede.appendChild(el('p', 'md-latest'));
        latest.hidden = true;
        var source = link(LETTERBOXD, 'md-source');
        var sourceName = source.appendChild(el('span'));
        source.appendChild(icon(ICON.out, '2.2'));
        head.appendChild(opensNewTab(source));
        panel.appendChild(head);

        var tools = el('div', 'md-tools');
        tools.hidden = true;
        var search = el('div', 'md-search');
        search.appendChild(icon(ICON.search));
        var qLabel = el('label', 'md-sr', 'Search this shelf');
        qLabel.htmlFor = uid + '-q';
        search.appendChild(qLabel);
        var q = el('input');
        q.type = 'search'; q.id = uid + '-q'; q.autocomplete = 'off'; q.spellcheck = false;
        search.appendChild(q);
        tools.appendChild(search);
        var chips = el('div', 'md-chips');
        chips.setAttribute('role', 'group');
        chips.setAttribute('aria-label', 'Show');
        tools.appendChild(chips);
        var selects = el('div', 'md-selects');
        function selBox(label, key) {
            var l = el('label', 'md-sel');
            l.appendChild(el('span', 'md-sel-k', label));
            var s = l.appendChild(el('select'));
            s.dataset.key = key;
            selects.appendChild(l);
            return s;
        }
        var fRating = selBox('Rating', 'rating');
        var fDecade = selBox('Decade', 'decade');
        var fSort = selBox('Sort', 'sort');
        tools.appendChild(selects);
        panel.appendChild(tools);

        var status = el('p', 'md-status');
        status.setAttribute('aria-live', 'polite');
        var statusText = status.appendChild(el('span', null, 'Loading the shelves…'));
        panel.appendChild(status);
        var grid = panel.appendChild(el('div', 'md-grid'));
        var empty = panel.appendChild(el('div'));
        empty.hidden = true;
        var pager = el('nav', 'md-pager');
        pager.setAttribute('aria-label', 'Media diet pages');
        pager.hidden = true;
        panel.appendChild(pager);

        app.appendChild(tabs);
        app.appendChild(panel);

        // ---- Hash routing (opt-in, prefixed so it never fights the host page) ----
        function hashTab() {
            if (opt.prefix === null) return null;
            var h = (location.hash || '').replace(/^#/, '').split(/[/?]/)[0].toLowerCase();
            var p = opt.prefix.toLowerCase();
            if (h.slice(0, p.length) !== p) return null;
            h = h.slice(p.length);
            return SHELVES.hasOwnProperty(h) ? h : null;
        }
        function writeHash(key, replace) {
            if (opt.prefix === null) return;
            var want = '#' + opt.prefix + key;
            if (location.hash === want) return;
            // A page that owns its hash gets history entries; an embedded shelf only updates the URL in place
            try { history[(replace || opt.prefix) ? 'replaceState' : 'pushState'](null, '', want); } catch (e) {}
        }

        // ---- Controls ----
        function fillSelect(sel, options, value) {
            sel.textContent = '';
            options.forEach(function (o) { var op = el('option', null, o[1]); op.value = o[0]; sel.appendChild(op); });
            sel.value = options.some(function (o) { return o[0] === value; }) ? value : options[0][0];
            return sel.value;
        }
        function buildControls() {
            var key = current, st = state[key], shelf = SHELVES[key], list = items[key];
            var hasRatings = list.some(function (i) { return i.rating; });
            q.placeholder = typeof shelf.search === 'function' ? shelf.search(list) : shelf.search;
            q.value = st.q;

            chips.textContent = '';
            var defs = chipList(key, list);
            if (!defs.some(function (d) { return d[0] === st.chip; })) st.chip = 'all';
            defs.forEach(function (d) {
                var b = el('button', 'md-chip', d[1]);
                b.type = 'button';
                b.dataset.chip = d[0];
                b.setAttribute('aria-pressed', String(st.chip === d[0]));
                b.appendChild(el('span', 'md-chip-n', d[2]));
                chips.appendChild(b);
            });
            chips.hidden = chips.children.length < 2;

            fRating.parentNode.hidden = !hasRatings;
            if (hasRatings) {
                var ro = key === 'watching'
                    ? [['any', 'Any'], ['5', '★★★★★'], ['4.5', '4½★ & up'], ['4', '4★ & up'], ['3', '3★ & up'], ['under3', 'Under 3★'], ['unrated', 'Unrated']]
                    : [['any', 'Any'], ['5', '★★★★★'], ['4', '4★ & up'], ['3', '3★ & up'], ['unrated', 'Unrated']];
                st.rating = fillSelect(fRating, ro, st.rating);
            } else st.rating = 'any';

            var decades = [];
            list.forEach(function (i) { if (i.decade && decades.indexOf(i.decade) === -1) decades.push(i.decade); });
            decades.sort().reverse();
            fDecade.parentNode.hidden = key !== 'watching' || decades.length < 2;
            if (!fDecade.parentNode.hidden) st.decade = fillSelect(fDecade, [['any', 'Any']].concat(decades.map(function (d) { return [d, d]; })), st.decade);
            else st.decade = 'any';

            var so = [['new', key === 'watching' ? 'Recently watched' : 'Newest'], ['old', 'Oldest']];
            if (hasRatings) so.push(['rated', 'Highest rated']);
            if (key === 'watching') so.push(['release', 'Release year']);
            so.push(['title', 'Title A–Z']);
            st.sort = fillSelect(fSort, so, st.sort);

            tools.hidden = list.length < 2;
        }

        function renderPager(page, pages) {
            pager.textContent = '';
            pager.hidden = pages < 2;
            if (pages < 2) return;
            pager.appendChild(stepBtn(-1, page <= 1, page - 1));
            if (!opt.compact) {
                pageList(page, pages).forEach(function (p) {
                    if (p === '…') { pager.appendChild(el('span', 'md-pg-gap md-pg-num', '…')).setAttribute('aria-hidden', 'true'); return; }
                    var b = el('button', 'md-pg md-pg-num', p);
                    b.type = 'button';
                    b.dataset.page = String(p);
                    b.setAttribute('aria-label', 'Page ' + p);
                    if (p === page) b.setAttribute('aria-current', 'page');
                    pager.appendChild(b);
                });
            }
            pager.appendChild(el('span', 'md-pg-of', 'Page ' + page + ' of ' + pages));
            pager.appendChild(stepBtn(1, page >= pages, page + 1));
        }

        // ---- Render the current shelf ----
        function render(fresh) {
            var key = current, st = state[key], shelf = SHELVES[key], all = items[key];
            var shown = sorted(all.filter(function (i) { return matches(i, st, shelf); }), st, key);
            var per = opt.perPage;
            var pages = Math.max(1, Math.ceil(shown.length / per));
            st.page = Math.min(Math.max(1, st.page), pages);
            var start = (st.page - 1) * per;
            var slice = shown.slice(start, start + per);

            grid.textContent = '';
            grid.className = 'md-grid' + (key === 'listening' ? ' is-list' : '') + (fresh ? ' is-fresh' : '');
            slice.forEach(function (it) { grid.appendChild(CARD[key](it)); });

            empty.textContent = '';
            empty.hidden = slice.length > 0 || !loaded;
            if (!slice.length && loaded) empty.appendChild(emptyState(all.length ? FILTERED : shelf.empty, opt.heading));

            var filtered = st.q || st.chip !== 'all' || st.rating !== 'any' || st.decade !== 'any';
            var noun = typeof shelf.noun === 'function' ? shelf.noun(all) : shelf.noun, text = '';
            if (!loaded) text = 'Loading the shelves…';
            else if (!all.length) text = '';
            else if (shown.length > per) text = 'Showing ' + (start + 1) + '–' + (start + slice.length) + ' of ' + plural(shown.length, noun[0], noun[1]) + (filtered ? ' (of ' + all.length + ')' : '');
            else if (filtered) text = shown.length + ' of ' + plural(all.length, noun[0], noun[1]);
            else text = plural(all.length, noun[0], noun[1]);
            statusText.textContent = text;
            var old = status.querySelector('.md-clear');
            if (old) old.remove();
            if (filtered && shown.length) {
                var c = el('button', 'md-clear', 'Clear filters');
                c.type = 'button';
                c.setAttribute('data-clear', '');
                status.appendChild(c);
            }
            renderPager(st.page, pages);
        }

        function selectTab(key, focus) {
            current = key;
            ORDER.forEach(function (k) {
                var on = k === key;
                tabEl[k].setAttribute('aria-selected', String(on));
                tabEl[k].tabIndex = on ? 0 : -1;
            });
            var shelf = SHELVES[key];
            panel.setAttribute('aria-labelledby', tabEl[key].id);
            dek.textContent = shelf.dek;
            var line = loaded ? summaryLine(key, items[key], todayISO()) : '';
            latest.textContent = line;
            latest.hidden = !line;
            source.hidden = !shelf.href;
            if (shelf.href) { source.href = shelf.href; sourceName.textContent = shelf.source; }
            if (opt.docTitle) document.title = shelf.name + ' · ' + opt.docTitle;
            buildControls();
            render(true);
            if (focus) tabEl[key].focus();
        }

        // ---- Wiring ----
        tabs.addEventListener('click', function (e) {
            var t = e.target.closest('[data-tab]');
            if (!t) return;
            writeHash(t.dataset.tab, false);
            selectTab(t.dataset.tab);
        });
        tabs.addEventListener('keydown', function (e) {
            var i = ORDER.indexOf(current), next = null;
            if (e.key === 'ArrowRight') next = ORDER[(i + 1) % ORDER.length];
            else if (e.key === 'ArrowLeft') next = ORDER[(i + ORDER.length - 1) % ORDER.length];
            else if (e.key === 'Home') next = ORDER[0];
            else if (e.key === 'End') next = ORDER[ORDER.length - 1];
            if (!next) return;
            e.preventDefault();
            writeHash(next, true);
            selectTab(next, true);
        });
        if (opt.prefix !== null) {
            var onHash = function () {
                var k = hashTab();
                // Only a page that owns the hash falls back to the first shelf on a bare URL;
                // #about, #top and friends are someone else's and leave the shelf alone.
                if (!k && opt.prefix === '' && !location.hash) k = ORDER[0];
                if (k && k !== current) selectTab(k);
            };
            window.addEventListener('hashchange', onHash);
            window.addEventListener('popstate', onHash);
        }

        var typing;
        q.addEventListener('input', function () {
            clearTimeout(typing);
            var v = q.value;
            typing = setTimeout(function () { state[current].q = v.trim(); state[current].page = 1; render(); }, 120);
        });
        chips.addEventListener('click', function (e) {
            var b = e.target.closest('[data-chip]');
            if (!b) return;
            state[current].chip = b.dataset.chip;
            state[current].page = 1;
            [].forEach.call(chips.children, function (c) { c.setAttribute('aria-pressed', String(c === b)); });
            render();
        });
        [fRating, fDecade, fSort].forEach(function (sel) {
            sel.addEventListener('change', function () { state[current][sel.dataset.key] = sel.value; state[current].page = 1; render(); });
        });
        pager.addEventListener('click', function (e) {
            var b = e.target.closest('[data-page]');
            if (!b || b.disabled) return;
            var dir = b.dataset.dir;
            state[current].page = parseInt(b.dataset.page, 10) || 1;
            render(true);
            // New page: if its first row is out of sight, bring the shelf's tabs back into view and
            // start keyboard/screen-reader users at the top of the new page. Otherwise stay put.
            var offset = parseFloat(getComputedStyle(app).getPropertyValue('--md-offset')) || 0;
            if (grid.getBoundingClientRect().top < offset) {
                tabs.scrollIntoView({ block: 'start' });
                try { panel.focus({ preventScroll: true }); } catch (err) { panel.focus(); }
            } else {
                var again = dir ? pager.querySelector('[data-dir="' + dir + '"]:not(:disabled)') : pager.querySelector('[aria-current="page"]');
                try { (again || panel).focus({ preventScroll: true }); } catch (err) { (again || panel).focus(); }
            }
        });
        panel.addEventListener('click', function (e) {
            if (!e.target.closest('[data-clear]')) return;
            state[current] = { q: '', chip: 'all', rating: 'any', decade: 'any', sort: state[current].sort, page: 1 };
            buildControls();
            render();
            try { panel.focus({ preventScroll: true }); } catch (err) { panel.focus(); }
        });

        // ---- The newest three covers, fanned (standalone masthead) ----
        function renderStack(box) {
            var all = items.watching.concat(items.reading, items.listening).filter(function (i) { return i.image; });
            all.sort(byDate);
            var pick = all.slice(0, 3);
            box.textContent = '';
            if (pick.length < 2) { box.hidden = true; return; }
            pick.forEach(function (it) {
                var a = link(it.url, 'md-stack-item');
                if (it.url) a.setAttribute('aria-label', it.title);
                a.appendChild(cover(it.image, tile(it.kind === 'book' ? 'book' : 'film', it.title, it.year || it.author || '')).firstChild);
                box.appendChild(a);
            });
            box.appendChild(el('span', 'md-stack-cap', 'Lately'));
            box.hidden = false;
        }

        // ---- Go ----
        var deep = hashTab();
        selectTab(deep || ORDER[0]);
        load(opt.root).then(function (data) {
            ORDER.forEach(function (k) { items[k] = data[k]; });
            loaded = true;
            ORDER.forEach(function (k) { countEl[k].textContent = SHELVES[k].count(items[k].length, items[k]); });
            if (opt.synced && data.updated) opt.synced.textContent = 'Synced ' + fmtDate(data.updated);
            if (opt.stack) renderStack(opt.stack);
            selectTab(current);
            // An embedded shelf opened from a link like /#md-reading scrolls itself into view
            // (no element carries that id, so the browser won't). Re-aim once the page has
            // finished loading, unless the visitor has already scrolled somewhere else.
            if (deep && opt.prefix) {
                jumpTo(app);
                var y = window.pageYOffset;
                if (document.readyState !== 'complete') {
                    window.addEventListener('load', function () { if (Math.abs(window.pageYOffset - y) < 4) jumpTo(app); }, { once: true });
                }
            }
        });
    }

    // The data-only helpers, for tests (node tests/... requires this file; no DOM needed)
    if (typeof module === 'object' && module && module.exports) {
        module.exports = { summaryLine: summaryLine, buildShelves: buildShelves, chipList: chipList };
    }
    if (!HAS_DOM) return;

    function init() {
        [].forEach.call(document.querySelectorAll('.md-app'), mount);
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
