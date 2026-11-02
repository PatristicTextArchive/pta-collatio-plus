/* Interface language (German / English).

   The interface is written in German. For English, the strings in the page are translated
   with the dictionary in i18n-en.js (German → English): text nodes and the attributes title,
   placeholder, aria-label and data-tip, also everything that is added later (a MutationObserver
   watches the page). Keys may contain placeholders such as {n}; they match any text there.
   Code can also call t("German text", {n: 3}) directly.

   Language: ?lang=de|en (set by the switch), else the choice stored in the browser, else the
   browser language.
   ?i18n=collect records every string without a translation in window.__ptaMissing (for
   maintaining the dictionary). */
(function () {
  "use strict";
  const KEY = "pta-ui-lang";
  const ok = l => l === "de" || l === "en";
  let lang = null, collect = false;
  try {
    const q = new URLSearchParams(location.search);
    lang = q.get("lang");
    collect = q.get("i18n") === "collect";
  } catch (e) { /* no URL parameters */ }
  if (!ok(lang)) lang = window.PTA_LANG || null;
  if (!ok(lang)) { try { lang = localStorage.getItem(KEY); } catch (e) { lang = null; } }
  if (!ok(lang)) lang = /^de/i.test(navigator.language || "de") ? "de" : "en";
  document.documentElement.lang = lang;

  const norm = s => s.replace(/\s+/g, " ").trim();
  const EN = {};
  for (const [k, v] of Object.entries(window.PTA_EN || {})) EN[norm(k)] = v;
  const exact = new Map();
  const patterns = [];
  const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  for (const [k, v] of Object.entries(EN)) {
    if (!/\{\w+\}/.test(k)) { exact.set(k, v); continue; }
    const names = [];
    const src = k.split(/(\{\w+\})/).map(part => {
      const m = part.match(/^\{(\w+)\}$/);
      if (m) { names.push(m[1]); return "([\\s\\S]*?)"; }
      return reEsc(part);
    }).join("");
    patterns.push({ re: new RegExp("^" + src + "$"), names, v, len: k.length, src });
  }
  patterns.sort((a, b) => b.len - a.len);   // most specific first
  // index by the first two characters of the literal prefix (patterns starting with a
  // placeholder are tried for every string)
  const byPrefix = new Map(), open = [];
  for (const p of patterns) {
    const lit = p.src.split("([\\s\\S]*?)")[0].replace(/\\/g, "");
    if (lit.length < 2) { open.push(p); continue; }
    const k = lit.slice(0, 2);
    if (!byPrefix.has(k)) byPrefix.set(k, []);
    byPrefix.get(k).push(p);
  }

  const fill = (s, v) => v ? s.replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? v[k] : m)) : s;
  /** Translate a German source string (for use in code). */
  // "Text|context" distinguishes words with two meanings; German shows the part before "|"
  function t(s, v) {
    const k = norm(s), de = k.includes("|") ? k.split("|")[0] : s;
    return fill(lang === "en" && EN[k] != null ? EN[k] : de, v);
  }

  const LATIN = /[A-Za-zÄÖÜäöüß]{2}/;
  const missing = window.__ptaMissing = new Set();
  const note = s => { if (collect && LATIN.test(s)) missing.add(s.replace(/\d+([.,]\d+)?/g, "{n}")); };

  /** Translation of a displayed string, or null. */
  function lookup(s) {
    if (exact.has(s)) return exact.get(s);
    const cand = (byPrefix.get(s.slice(0, 2)) || []).concat(open);
    for (const p of cand) {
      const m = p.re.exec(s);
      if (!m) continue;
      const vals = {};
      p.names.forEach((n, i) => { const x = m[i + 1]; vals[n] = exact.has(x) ? exact.get(x) : x; });
      return fill(p.v, vals);
    }
    return null;
  }
  function tr(s) {
    if (!s || !LATIN.test(s)) return s;
    const m = s.match(/^(\s*)([\s\S]*?)(\s*)$/);
    const core = norm(m[2]);
    let out = lookup(core);
    if (out == null) {
      // surrounding brackets or punctuation
      const p = core.match(/^([(„“"«‹\[–—·•…\s]*)([\s\S]*?)([)“”"»›\].:,;!?…–—·\s]*)$/);
      if (p && p[2] && p[2] !== core) {
        const inner = lookup(p[2]);
        if (inner != null) out = p[1] + inner + p[3];
      }
    }
    if (out == null && / · /.test(core)) {
      // parts joined with " · "
      const parts = core.split(" · ");
      const done = parts.map(x => tr(x));
      if (done.some((x, i) => x !== parts[i])) out = done.join(" · ");
    }
    if (out == null) { note(core); return s; }
    return m[1] + out + m[3];
  }

  const ATTRS = ["title", "placeholder", "aria-label", "data-tip"];
  const SKIP = "script, style, textarea, code, kbd, [translate=no], .notranslate";
  function skipped(el) { return !el || (el.closest && el.closest(SKIP)); }
  function translateNode(node) {
    if (node.nodeType === 3) {
      if (!skipped(node.parentElement)) {
        const v = node.nodeValue, x = tr(v);
        if (x !== v) node.nodeValue = x;
      }
      return;
    }
    if (node.nodeType !== 1 || skipped(node)) return;
    for (const a of ATTRS) {
      if (!node.hasAttribute(a)) continue;
      const v = node.getAttribute(a), x = tr(v);
      if (x !== v) node.setAttribute(a, x);
    }
    if (node.tagName === "INPUT" && (node.type === "button" || node.type === "submit")) {
      const x = tr(node.value);
      if (x !== node.value) node.value = x;
    }
    for (const c of node.childNodes) translateNode(c);
  }

  let observer = null;
  function start() {
    if (lang !== "en" && !collect) return;
    translateNode(document.body);
    if (document.title) document.title = tr(document.title);
    observer = new MutationObserver(list => {
      observer.disconnect();
      for (const m of list) {
        if (m.type === "childList") m.addedNodes.forEach(translateNode);
        else if (m.type === "characterData") translateNode(m.target);
        else if (m.type === "attributes") translateNode(m.target.nodeType === 1 ? shallow(m.target, m.attributeName) : m.target);
      }
      observe();
    });
    observe();
  }
  function shallow(el, attr) {
    const v = el.getAttribute(attr);
    if (v != null && !skipped(el)) { const x = tr(v); if (x !== v) el.setAttribute(attr, x); }
    return document.createTextNode("");
  }
  function observe() {
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }

  function setLang(l) {
    if (!ok(l)) return;
    try { localStorage.setItem(KEY, l); localStorage.setItem("pta-varianz-lang", l); } catch (e) { /* storage blocked */ }
    // the language also goes into the address (?lang=), so the choice holds when the browser
    // does not allow site storage; a changed query string always loads the page anew
    const u = new URL(location.href);
    u.searchParams.set("lang", l);
    location.replace(u.toString());
  }

  window.PTAI18N = { lang, t, tr, setLang, translate: translateNode, missing };
  window.t = t;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
