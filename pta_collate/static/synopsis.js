/* Synopsis renderer – shared by the application and the stand-alone HTML export. */
(function () {
  "use strict";

  const CLASSES = [
    { id: "ortho", mk: "~", label: "Orthographisch",
      desc: "Gleicher orthographischer Schlüssel wie der Vergleichstext: Unterschied nur in Akzenten, Spiritus, Itazismus (ει/ι/η/οι/υ, αι/ε, ο/ω), Doppelkonsonanten, Groß-/Kleinschreibung oder Interpunktion." },
    { id: "subst", mk: "≠", label: "Substantiell", desc: "Anderer Wortlaut als der Vergleichstext." },
    { id: "omit", mk: "∅", label: "Auslassung", desc: "Der Zeuge hat hier keinen Text, der Vergleichstext schon." },
    { id: "add", mk: "+", label: "Hinzufügung", desc: "Der Zeuge hat Text, den der Vergleichstext nicht hat." },
    { id: "transp", mk: "⇄", label: "Umstellung",
      desc: "Dieselben Wörter in anderer Reihenfolge an derselben Stelle (⇄) oder weite Umstellung: Auslassung hier, Zusatz an anderer Stelle (↔ verknüpft, ↔? Vorschlag)." },
    { id: "gap", mk: "?", label: "Unleserlich/Lücke", desc: "Text unleserlich, beschädigt oder vom Schreiber freigelassen (gap)." },
    { id: "corr", mk: "c", label: "Korrektur in der Hs.",
      desc: "Die Handschrift korrigiert hier (del, add, subst). Die Lesart vor der Korrektur (*) steht blau unter der Zelle." },
  ];
  const MK = Object.fromEntries(CLASSES.map(c => [c.id, c.mk]));

  // translation (i18n.js); without it the German source text is used
  const t = (s, v) => (window.t ? window.t(s, v) : (v ? s.replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? v[k] : m)) : s));
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const segLabel = seg => seg === "0" ? t("Titel / Vorspann") : t("Abschnitt {n}", { n: esc(seg) });
  const fold = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  /* ------------------------------------------------------------ columns */
  function columns(data, mode) {
    // mode "ms": one column per manuscript (pc shown, ac below if different); "layers": one per layer
    const cols = [];
    if (mode === "layers") {
      for (const w of data.witnesses) cols.push({ key: w.id, label: w.label, name: w.name, main: w.id, ac: null, ms: w.ms });
      return cols;
    }
    const seen = new Map();
    for (const w of data.witnesses) {
      if (!seen.has(w.ms)) { seen.set(w.ms, { key: w.ms, label: w.siglum, name: w.name, main: null, ac: null, ms: w.ms }); cols.push(seen.get(w.ms)); }
      const col = seen.get(w.ms);
      if (w.layer === "ac") col.ac = w.id; else col.main = w.id;
    }
    for (const c of cols) if (!c.main) { c.main = c.ac; c.ac = null; }
    return cols;
  }

  /* --------------------------------------------------------- comparison */
  function readingOf(u, cid) { return u.readings.find(r => r.wits.includes(cid)); }

  function baseReading(u, base, data) {
    if (!u.variant) return u.readings[0];
    if (base === "lemma" && u.lem) return u.readings.find(r => r.id === u.lem);
    if (base && base.startsWith("wit:")) {
      const ms = base.slice(4);
      const ids = data.witnesses.filter(w => w.ms === ms).map(w => w.id);
      const cid = ids.find(id => id in u.cells && !id.endsWith("_ac")) || ids.find(id => id in u.cells);
      if (cid) return readingOf(u, cid);
    }
    if (u.lem) return u.readings.find(r => r.id === u.lem);
    // majority, counting each manuscript once (post correctionem layer)
    // ties: a reading with text wins over an omission
    let best = null, bestN = -1;
    for (const r of u.readings) {
      const n = r.wits.filter(w => !w.endsWith("_ac")).length;
      if (n > bestN || (n === bestN && best && !best.c && r.c)) { best = r; bestN = n; }
    }
    return best;
  }

  function cellClass(u, cid, base) {
    const cell = u.cells[cid];
    if (!cell) return "absent";
    if (!u.variant) return "same";
    const r = readingOf(u, cid);
    if (r && base && r.id === base.id) return "same";
    if (r && r.gap) return "gap";
    if (!cell.c && base && base.c) return "omit";
    if (cell.c && base && !base.c) return "add";
    if (r && r.type === "transposition") return "transp";
    if (base && cell.o && cell.o === base.o) return "ortho";
    if (base && cell.c === base.c) return "same";
    return "subst";
  }

  function rowClasses(u, cols, base) {
    const set = new Set();
    if (u.link || u.suggest) set.add("transp");
    for (const col of cols) {
      for (const cid of [col.main, col.ac]) {
        if (!cid || !(cid in u.cells)) continue;
        set.add(cellClass(u, cid, base));
        if ((u.cells[cid].flags || []).includes("corr")) set.add("corr");
      }
      if (col.ac && u.cells[col.ac] && u.cells[col.main] && u.cells[col.ac].c !== u.cells[col.main].c) set.add("corr");
    }
    return set;
  }

  // signs in the margin of the manuscript (<g>): shown quietly before the text
  const SIGNS = { diple: ["›", "Diple"], doubled_diple: ["»", "Doppelte Diple"], paragraphos: ["⸏", "Paragraphos"],
    obelos: ["÷", "Obelos"], dotted_obelos: ["⸓", "Obelos mit Punkten"] };
  function signsHTML(cell) {
    return (cell.flags || []).filter(f => f.startsWith("g:")).map(f => {
      const [sym, name] = SIGNS[f.slice(2)] || ["·", f.slice(2)];
      return `<span class="sign" title="${esc(name)}">${sym}</span>`;
    }).join("");
  }

  function tokenHTML(cell, tokens) {
    if (!cell) return "";
    if (!cell.c && !cell.t) return '<span class="empty-sign">–</span>';
    if (!(cell.flags || []).includes("unclear") || !cell.tokens) return esc(cell.t);
    return cell.tokens.map(t => {
      const tok = tokens && tokens[t];
      const text = tok ? tok.t : "";
      return tok && tok.flags && tok.flags.includes("unclear") ? `<span class="unclear">${esc(text)}</span>` : esc(text);
    }).join(" ");
  }

  /* ------------------------------------------------------------ help */
  // <span class="info" data-tip="…">i</span> anywhere in the page shows an explanation on
  // hover and keyboard focus. One floating box, kept inside the window.
  function tip(text) {
    return `<span class="info" tabindex="0" role="img" aria-label="${esc(text)}" data-tip="${esc(text)}">i</span>`;
  }
  function installTips(doc) {
    doc = doc || document;
    if (doc.__ptaTips) return;
    doc.__ptaTips = true;
    const box = doc.createElement("div");
    box.className = "tipbox";
    box.hidden = true;
    box.setAttribute("aria-hidden", "true");
    doc.body.appendChild(box);
    let cur = null;
    const show = el => {
      cur = el;
      box.textContent = el.getAttribute("data-tip");
      box.hidden = false;
      const r = el.getBoundingClientRect();
      const bw = box.offsetWidth, bh = box.offsetHeight;
      const x = Math.max(8, Math.min(r.left + r.width / 2 - bw / 2, window.innerWidth - bw - 8));
      let y = r.bottom + 6;
      if (y + bh > window.innerHeight - 8) y = Math.max(8, r.top - bh - 6);
      box.style.left = x + "px";
      box.style.top = y + "px";
    };
    const hide = () => { cur = null; box.hidden = true; };
    doc.addEventListener("mouseover", e => {
      const el = e.target.closest && e.target.closest("[data-tip]");
      if (el && el !== cur) show(el); else if (!el && cur) hide();
    });
    doc.addEventListener("focusin", e => { const el = e.target.closest && e.target.closest("[data-tip]"); if (el) show(el); });
    doc.addEventListener("focusout", hide);
    doc.addEventListener("scroll", hide, true);
    doc.addEventListener("keydown", e => { if (e.key === "Escape") hide(); });
  }

  const VIEW_KEY = "pta-synopsis-view";
  function loadView() { try { return JSON.parse(localStorage.getItem(VIEW_KEY) || "{}"); } catch (e) { return {}; } }
  function saveView(v) { try { localStorage.setItem(VIEW_KEY, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } }

  /* ------------------------------------------------------------- render */
  function create(root, data, opts) {
    opts = Object.assign({ readonly: false, onSelect: null, base: (data.settings && data.settings.base) || "majority" }, opts || {});
    const state = {
      data, base: opts.base, mode: "ms", rotate: false, only: "all", filter: new Set(), seg: "", q: "",
      selected: opts.selected || null, pages: true, limit: 300,
      view: Object.assign({ font: 17, width: 14, compact: false, hidden: [], drawer: 430, graph: false, graphH: 300, graphMode: "context", graphCtx: 6, graphOrtho: false }, loadView()),
    };
    // full token info (flags) for unclear marking when available
    const tokenFlags = {};
    for (const u of data.units) for (const cid in u.cells) {
      const c = u.cells[cid];
      if ((c.flags || []).includes("unclear")) for (const t of c.tokens || []) tokenFlags[t] = true;
    }

    root.innerHTML = `
      <div class="syn-shell"><div class="syn-main">
        <div class="syn-tools">
          <label>Vergleich mit <select data-k="base"></select>${tip("Bezugspunkt für Farben und Zeichen: Abweichungen von der Mehrheit der Handschriften (jede einmal gezählt, nach Korrektur), vom gewählten Lemma oder von einem Leitzeugen.")}</label>
          <label>Zeigen <select data-k="only">
            <option value="all">alle Stellen</option>
            <option value="var">nur Variationsstellen</option>
            <option value="sub">ohne rein orthographische</option>
          </select>${tip("Alle Stellen: auch der übereinstimmende Text (grau). Nur Variationsstellen: nur Stellen mit Varianz. Ohne rein orthographische: blendet Stellen aus, an denen alle Abweichungen orthographisch sind.")}</label>
          <label>Abschnitt <select data-k="seg"><option value="">alle</option></select></label>
          <label class="check"><input type="checkbox" data-k="layers"> Korrekturschichten als eigene Spalten${tip("Aus: eine Spalte je Handschrift mit dem Text nach der Korrektur (ᶜ), die ursprüngliche Lesart (*) steht blau darunter. An: je eine Spalte für * und ᶜ.")}</label>
          <label class="check"><input type="checkbox" data-k="rotate"> Zeugen als Zeilen${tip("Dreht die Tabelle: eine Zeile je Zeuge, eine Spalte je Stelle. Übersichtlich für kurze Abschnitte.")}</label>
          <label>Suche <input type="text" data-k="q" size="14" placeholder="Wort">${tip("Zeigt nur Stellen, deren Text in irgendeinem Zeugen das Suchwort enthält; Akzente und Groß-/Kleinschreibung werden ignoriert.")}</label>
          <span class="muted" data-k="count"></span>
        </div>
        <div class="syn-tools syn-view" aria-label="Darstellung">
          <label>Schrift <input type="range" data-v="font" min="11" max="24" step="1"><span class="muted" data-o="font"></span></label>
          <label>Spaltenbreite <input type="range" data-v="width" min="4" max="30" step="1"><span class="muted" data-o="width"></span></label>
          <label class="check"><input type="checkbox" data-v="compact"> Kompakt${tip("Jede Zelle einzeilig, ohne Seitenangaben. Der volle Text erscheint beim Darüberfahren mit der Maus.")}</label>
          <span class="wit-pick"><button type="button" class="btn small" data-k="wits" aria-expanded="false" data-tip="Einzelne Handschriften ausblenden. Ändert nur die Anzeige, nicht die Kollation.">Zeugen auswählen</button><span class="muted" data-k="hidden-count"></span>
            <div class="wit-pop" hidden></div></span>
          <label class="check"><input type="checkbox" data-v="graph"> Graph${tip("Zeigt unter der Synopse den Variantengraphen: jede Lesart ein Knoten, jede Handschrift ein Pfad. Kantendicke = Zahl der Zeugen; gestrichelte Umgehung unterhalb = Auslassung; Bögen oben = weite Umstellung (gestrichelt: Vorschlag). Klick auf einen Knoten wählt die Stelle.")}</label>
          <button type="button" class="btn small" data-k="print" data-tip="Druckt die Synopse mit den aktuellen Filtern und allen eingeblendeten Zeugen im Querformat. Passen nicht alle Zeugen auf die Seitenbreite, werden sie in Gruppen geteilt; die Gruppen eines Abschnitts von Stellen stehen auf aufeinanderfolgenden Seiten. Auch über die Druckfunktion des Browsers.">Drucken</button>
          <button type="button" class="btn small" data-k="reset-view" data-tip="Schrift, Spaltenbreite, Kompaktansicht und ausgeblendete Zeugen zurück auf die Grundeinstellung. Diese Einstellungen merkt sich der Browser.">Ansicht zurücksetzen</button>
        </div>
        <div class="legend" role="group" aria-label="Variantentypen filtern"></div>
        <div class="syn-scroll"><table class="syn" translate="no"></table></div>
        <section class="graph-panel" hidden aria-label="Variantengraph">
          <div class="graph-resize" title="Höhe des Graphen ziehen" aria-hidden="true"></div>
          <div class="graph-head">
            <span class="graph-title">Variantengraph</span>
            <label class="check"><input type="radio" name="gmode" value="context"> Umfeld der gewählten Stelle, ±<input type="number" data-g="ctx" min="1" max="60" class="num small"> Stellen</label>
            <label class="check"><input type="radio" name="gmode" value="whole"> ganzer Text bzw. gewählter Abschnitt</label>
            <label class="check"><input type="checkbox" data-g="ortho"> orthographische Varianten zusammenfassen${tip("Lesarten mit gleichem orthographischem Schlüssel (Itazismus, Akzente, Doppelkonsonanten) werden ein Knoten. Macht den Graphen übersichtlicher; die Schreibweisen stehen im Tooltip des Knotens.")}</label>
            <span class="graph-key"><span class="gk gk-same"></span>Vergleichstext <span class="gk gk-ortho"></span>orthographisch <span class="gk gk-subst"></span>substantiell <span class="gk gk-add"></span>Hinzufügung <span class="gk gk-transp"></span>Umstellung <span class="gk gk-ed"></span>Herausgeber <span class="gk gk-fam"></span>mit Untervarianten</span>
          </div>
          <div class="graph-host" translate="no"></div>
        </section>
      </div><div class="drawer-handle" title="Breite des Detailfensters ziehen" aria-hidden="true"></div><aside class="drawer hidden" aria-label="Details zur Stelle"></aside></div>`;
    const $ = sel => root.querySelector(sel);
    const baseSel = $('[data-k="base"]');
    baseSel.innerHTML = `<option value="majority">Mehrheit der Zeugen</option><option value="lemma">Lemma (falls gewählt)</option>` +
      columns(data, "ms").map(c => `<option value="wit:${esc(c.ms)}">${esc(c.label)}</option>`).join("");
    baseSel.value = state.base;
    const segSel = $('[data-k="seg"]');
    segSel.innerHTML += data.segments.map(s => `<option value="${esc(s)}">${esc(s === "0" ? t("Titel / Vorspann") : s)}</option>`).join("");

    baseSel.onchange = () => { state.base = baseSel.value; state.limit = 300; draw(); };
    $('[data-k="only"]').onchange = e => { state.only = e.target.value; state.limit = 300; draw(); };
    segSel.onchange = () => { state.seg = segSel.value; state.limit = 300; draw(); };
    $('[data-k="layers"]').onchange = e => { state.mode = e.target.checked ? "layers" : "ms"; draw(); };
    $('[data-k="rotate"]').onchange = e => { state.rotate = e.target.checked; draw(); };
    /* ---- view: size, compact mode, visible witnesses (remembered in this browser) */
    function applyView() {
      const v = state.view;
      root.style.setProperty("--syn-font", v.font + "px");
      root.style.setProperty("--syn-col", v.width + "em");
      root.style.setProperty("--drawer-w", v.drawer + "px");
      $('[data-o="font"]').textContent = v.font + " px";
      $('[data-o="width"]').textContent = v.width + " em";
      $('[data-v="font"]').value = v.font;
      $('[data-v="width"]').value = v.width;
      $('[data-v="compact"]').checked = v.compact;
      const n = v.hidden.length;
      $('[data-k="hidden-count"]').textContent = n ? ` ${n} ausgeblendet` : "";
      $('[data-v="graph"]').checked = !!v.graph;
      $(".graph-panel").hidden = !v.graph;
      root.style.setProperty("--graph-h", v.graphH + "px");
      for (const r of root.querySelectorAll('input[name="gmode"]')) r.checked = r.value === v.graphMode;
      $('[data-g="ctx"]').value = v.graphCtx;
      $('[data-g="ortho"]').checked = !!v.graphOrtho;
      saveView(v);
    }
    for (const el of root.querySelectorAll("[data-v]")) {
      el.oninput = () => {
        const k = el.dataset.v;
        state.view[k] = el.type === "checkbox" ? el.checked : Number(el.value);
        applyView();
        if (k === "compact") draw();
        if (k === "graph") drawGraph(true);
      };
      if (el.type === "checkbox") el.onchange = el.oninput;
    }
    $('[data-k="reset-view"]').onclick = () => { state.view = { font: 17, width: 14, compact: false, hidden: [], drawer: 430, graph: false, graphH: 300, graphMode: "context", graphCtx: 6, graphOrtho: false }; applyView(); draw(); };
    const pop = $(".wit-pop"), pickBtn = $('[data-k="wits"]');
    pickBtn.onclick = () => {
      const open = pop.hidden;
      pop.hidden = !open; pickBtn.setAttribute("aria-expanded", String(open));
      if (!open) return;
      const all = columns(data, "ms");
      pop.innerHTML = `<div class="row" style="margin:0 0 6px"><button type="button" class="btn small" data-all>alle</button><button type="button" class="btn small" data-none>keine</button></div>` +
        all.map(c => `<label class="check"><input type="checkbox" value="${esc(c.ms)}" ${state.view.hidden.includes(c.ms) ? "" : "checked"}> <b>${esc(c.label)}</b> <span class="muted">${esc(c.name || "")}</span></label>`).join("");
      const sync = () => { state.view.hidden = [...pop.querySelectorAll("input")].filter(x => !x.checked).map(x => x.value); applyView(); draw(); };
      for (const cb of pop.querySelectorAll("input")) cb.onchange = sync;
      pop.querySelector("[data-all]").onclick = () => { for (const cb of pop.querySelectorAll("input")) cb.checked = true; sync(); };
      pop.querySelector("[data-none]").onclick = () => { for (const cb of pop.querySelectorAll("input")) cb.checked = false; sync(); };
    };
    const closePop = () => { pop.hidden = true; pickBtn.setAttribute("aria-expanded", "false"); };
    document.addEventListener("click", e => { if (!pop.hidden && !e.target.closest(".wit-pick")) closePop(); });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && !pop.hidden) { closePop(); pickBtn.focus(); } });
    // drag the left edge of the detail panel
    const handle = root.querySelector(".drawer-handle");
    handle.onpointerdown = e => {
      handle.setPointerCapture(e.pointerId);
      const startX = e.clientX, startW = state.view.drawer;
      handle.onpointermove = ev => { state.view.drawer = Math.max(280, Math.min(900, startW + (startX - ev.clientX))); applyView(); };
      handle.onpointerup = () => { handle.onpointermove = null; };
    };
    for (const r of root.querySelectorAll('input[name="gmode"]'))
      r.onchange = () => { state.view.graphMode = r.value; applyView(); drawGraph(true); };
    $('[data-g="ctx"]').onchange = e => { state.view.graphCtx = Math.max(1, Math.min(60, Number(e.target.value) || 6)); applyView(); drawGraph(true); };
    $('[data-g="ortho"]').onchange = e => { state.view.graphOrtho = e.target.checked; applyView(); drawGraph(false); };
    const gres = $(".graph-resize");
    gres.onpointerdown = e => {
      gres.setPointerCapture(e.pointerId);
      const startY = e.clientY, startH = state.view.graphH;
      gres.onpointermove = ev => { state.view.graphH = Math.max(140, Math.min(window.innerHeight - 220, startH + (startY - ev.clientY))); applyView(); };
      gres.onpointerup = () => { gres.onpointermove = null; };
    };
    let graphView = null;
    function drawGraph(center) {
      if (!state.view.graph || !window.PTAGraph) return;
      if (!graphView) graphView = PTAGraph.Viewer($(".graph-host"), { onSelect: key => select(key, false) });
      const cols = shownColumns();
      const wits = cols.map(c => ({ id: c.main, label: c.label }));
      let units;
      if (state.view.graphMode === "whole") {
        units = data.units.filter(u => !state.seg || u.seg === state.seg);
      } else {
        let i = data.units.findIndex(u => u.key === state.selected);
        if (i < 0) i = Math.max(0, data.units.findIndex(u => u.variant));
        const n = state.view.graphCtx;
        units = data.units.slice(Math.max(0, i - n), i + n + 1);
      }
      const L = PTAGraph.layout(units, wits, { mergeOrtho: !!state.view.graphOrtho, baseOf: u => baseReading(u, state.base, data) });
      graphView.show(L, state.selected, center);
    }
    applyView();

    let qt;
    $('[data-k="q"]').oninput = e => { clearTimeout(qt); qt = setTimeout(() => { state.q = fold(e.target.value.trim()); draw(); }, 200); };

    function shownColumns() {
      const hidden = new Set(state.view.hidden);
      const cols = columns(data, state.mode).filter(c => !hidden.has(c.ms));
      return cols.length ? cols : columns(data, state.mode);
    }

    function visibleUnits(cols) {
      const out = [];
      data.units.forEach((u, i) => {
        if (state.seg && u.seg !== state.seg) return;
        const base = baseReading(u, state.base, data);
        const cls = rowClasses(u, cols, base);
        if (state.only === "var" && !u.variant) return;
        if (state.only === "sub" && (!u.variant || [...cls].every(c => c === "same" || c === "ortho" || c === "absent"))) return;
        if (state.filter.size && ![...state.filter].some(f => cls.has(f))) return;
        if (state.q && !Object.values(u.cells).some(c => fold(c.t).includes(state.q))) return;
        out.push({ u, i, base, cls });
      });
      return out;
    }

    function drawLegend(rows) {
      const counts = {};
      for (const r of rows) for (const c of r.cls) counts[c] = (counts[c] || 0) + 1;
      $(".legend").innerHTML = CLASSES.map(c => `
        <button type="button" data-f="${c.id}" aria-pressed="${state.filter.has(c.id)}" data-tip="${esc(t(c.desc))}\n\n${esc(t("Klick: nur Stellen mit „{label}“ zeigen.", { label: t(c.label) }))}">
          <span class="sw ${c.id === "corr" ? "" : "c-" + c.id}" style="${legendStyle(c.id)}">${c.mk}</span>${c.label}
          <span class="count">${counts[c.id] || 0}</span></button>`).join("") +
        `<span class="muted" style="font-size:13px;align-self:center">Klick filtert; mehrere möglich.</span>`;
      for (const b of root.querySelectorAll(".legend button")) b.onclick = () => {
        const f = b.dataset.f; state.filter.has(f) ? state.filter.delete(f) : state.filter.add(f); draw();
      };
    }
    function legendStyle(id) {
      const m = { ortho: "--v-ortho", subst: "--v-subst", omit: "--v-omit", add: "--v-add", transp: "--v-transp", gap: "--v-gap" };
      if (id === "corr") return "color:var(--v-corr);border:1px solid var(--v-corr)";
      return `background:var(${m[id]});color:var(${m[id]}-edge, var(--ink));${id === "gap" ? "outline:1px dashed var(--v-omit-edge)" : ""}`;
    }

    function cellHTML(u, col, base, isLemCell) {
      const cid = col.main;
      const cell = u.cells[cid];
      if (!cell) {
        if (!(u.absent || []).includes(cid)) return `<td class="absent">${t("nicht vorhanden")}</td>`;
        const kind = (u.absent_kind || {})[cid] || "lacuna";
        const [txt, ttl] = ABSENT[kind];
        return `<td class="absent a-${kind}" title="${esc(t(ttl))}">${esc(t(txt))}</td>`;
      }
      const cls = cellClass(u, cid, base);
      let inner = "";
      if (state.pages && cell.pages && cell.pages.length && cell._newpage) inner += cell._newpage.map(p => `<span class="pb">${esc(p)}</span>`).join("");
      const mk = cls !== "same" && cls !== "absent" ? `<span class="mk" aria-hidden="true">${MK[cls]}</span>` : "";
      inner += mk + signsHTML(cell) + tokenHTML(cell, tokensFor());
      if ((cell.flags || []).includes("corr") && !col.ac) inner += `<span class="badge-corr" title="${esc(t("Korrektur in der Handschrift"))}">c</span>`;
      if (col.ac && u.cells[col.ac] && u.cells[col.ac].c !== cell.c) {
        const ac = u.cells[col.ac];
        inner += `<span class="ac" title="ante correctionem"><span class="sg">${esc(col.label)}*</span> ${ac.t ? tokenHTML(ac, tokensFor()) : "–"}</span>`;
      }
      const lab = CLASSES.find(c => c.id === cls);
      const title = `${col.label}${lab ? " · " + t(lab.label) : ""}: ${cell.t || "–"}`;
      return `<td class="c-${cls}${isLemCell ? " lem-cell" : ""}" title="${esc(title)}">${inner}</td>`;
    }

    const ABSENT = {
      lacuna: ["Lücke", "Der Zeuge hat hier eine Lücke (im TEI lacunaStart/lacunaEnd)."],
      before: ["setzt später ein", "Der Zeuge beginnt erst nach dieser Stelle (im TEI witStart)."],
      after: ["endet vorher", "Der Zeuge endet vor dieser Stelle (im TEI witEnd)."],
    };
    const ED_LABEL = { conjecture: "conj.", correction: "corr.", proposition: "prop.", lacunam_indicavit: "lac." };
    function edMarks(u) {
      return (u.readings || []).filter(r => r.editorial).map(r => {
        const ttl = `${t({ conjecture: "Konjektur", correction: "Korrektur", proposition: "Vorschlag|proposition", lacunam_indicavit: "Lücke vermutet" }[r.editorial.kind])}${r.t ? ": " + r.t : ""}${r.id === u.lem ? " (Lemma)" : ""}`;
        return ` <span class="edmk${r.id === u.lem ? " is-lem" : ""}" title="${esc(ttl)}">${ED_LABEL[r.editorial.kind]}</span>`;
      }).join("");
    }

    let tokenCache = null;
    function tokensFor() {
      if (tokenCache) return tokenCache;
      tokenCache = {};
      const all = data.tokens || {};
      for (const k in all) tokenCache[k] = { t: all[k].t, flags: all[k].flags || [] };
      return tokenCache;
    }

    function markPages(rows, cols) {
      const last = {};
      for (const { u } of rows) for (const col of cols) {
        const cell = u.cells[col.main];
        if (!cell) continue;
        cell._newpage = [];
        for (const p of cell.pages || []) {
          if (last[col.main] !== p) { cell._newpage.push(p); last[col.main] = p; }
        }
      }
    }

    function draw() {
      drawTable();
      drawGraph(false);
    }

    function drawTable() {
      const sc = root.querySelector(".syn-scroll");
      const fresh = sc.cloneNode(false);           // drops scroll listeners of the previous draw
      fresh.appendChild(sc.querySelector("table.syn"));
      sc.replaceWith(fresh);
      fresh.scrollTop = 0;
      const cols = shownColumns();
      const rows = visibleUnits(cols);
      markPages(rows, cols);
      drawLegend(rows);
      const nvar = rows.filter(r => r.u.variant).length;
      $('[data-k="count"]').textContent = `${rows.length} Zeilen, davon ${nvar} Variationsstellen`;
      const table = $("table.syn");
      if (state.rotate) return drawRotated(table, rows, cols);
      table.className = "syn" + (state.view.compact ? " compact" : "");
      let html = `<thead><tr><th class="num" scope="col">${t("Stelle")}${tip(t("Nummer der Stelle. Zeichen dahinter: ● Lemma gewählt, ⇄ Umstellung, ↔ weite Umstellung verknüpft, ↔? weite Umstellung vorgeschlagen, ✎ Notiz, conj./corr./prop./lac. Lesart des Herausgebers (Konjektur, Korrektur, Vorschlag, vermutete Lücke).\nKlick auf eine Zeile öffnet die Details, die Tasten j und k springen zur nächsten bzw. vorigen Variationsstelle."))}</th>${cols.map(c =>
        `<th scope="col">${esc(c.label)}${c.ac ? ` <span class="muted" title="${esc(t("Korrekturen vorhanden"))}">*/ᶜ</span>` : ""}<span class="nm">${esc(c.name || "")}</span></th>`).join("")}</tr></thead><tbody>`;
      let seg = null;
      const shown = rows.slice(0, state.limit);
      for (const { u, i, base } of shown) {
        if (u.seg !== seg) {
          seg = u.seg;
          html += `<tr class="segrow"><td class="num"></td><td colspan="${cols.length}">${seg === "0" ? `<span data-tip="${esc(t("Text vor dem ersten Abschnittsanker (milestone bzw. div), meist Titel oder Überschrift des Werkes."))}">${segLabel(seg)}</span>` : segLabel(seg)}</td></tr>`;
        }
        const lemIds = u.lem ? (u.readings.find(r => r.id === u.lem) || { wits: [] }).wits : [];
        html += `<tr class="unit ${u.variant ? "var" : "inv"}${u.inserted ? " ins" : ""}${state.selected === u.key ? " sel" : ""}" data-key="${esc(u.key)}" tabindex="-1">
          <td class="num">${i + 1}${u.lem ? " ●" : ""}${u.transposition ? " ⇄" : ""}${u.link ? " ↔" : u.suggest ? ` <span title="${esc(t("vorgeschlagene weite Umstellung"))}">↔?</span>` : ""}${u.note ? " ✎" : ""}${u.inserted ? ` <span class="insmk" title="${esc(t("eingefügte Zeile"))}">+</span>` : ""}${edMarks(u)}</td>
          ${cols.map(c => cellHTML(u, c, base, lemIds.includes(c.main))).join("")}</tr>`;
      }
      if (rows.length > shown.length)
        html += `<tr class="more"><td class="num"></td><td colspan="${cols.length}"><button class="btn small" data-more>${t("Weitere {a} von {b} Zeilen zeigen", { a: Math.min(300, rows.length - shown.length), b: rows.length - shown.length })}</button></td></tr>`;
      html += "</tbody>";
      table.innerHTML = html;
      for (const tr of table.querySelectorAll("tr.unit")) tr.onclick = () => select(tr.dataset.key, true);
      const more = table.querySelector("[data-more]");
      if (more) {
        more.onclick = () => { const sc = root.querySelector(".syn-scroll").scrollTop; state.limit += 300; drawTable(); root.querySelector(".syn-scroll").scrollTop = sc; };
        const scroller = root.querySelector(".syn-scroll");
        // load more only when the person actually scrolls near the end (never in a loop on load)
        const onScroll = () => {
          if (scroller.scrollTop + scroller.clientHeight > scroller.scrollHeight - 600) {
            scroller.removeEventListener("scroll", onScroll);
            more.click();
          }
        };
        if (scroller.scrollHeight > scroller.clientHeight + 10) scroller.addEventListener("scroll", onScroll, { passive: true });
      }
    }

    // ---------------------------------------------------------------- print
    // The screen table is rendered lazily and may be wider than a page. For printing it is laid
    // out anew: every row of the current filter, the witnesses in groups that fit the page width
    // and – with several groups – the groups of each block of rows on consecutive pages, so that
    // all witnesses of a passage stay together.
    const PRINT = { pageW: 273, pageH: 186, numMM: 13, colMM: 30 };
    const MM = 96 / 25.4;      // CSS pixels per millimetre
    function buildPrint() {
      removePrint();
      const cols = shownColumns();
      const rows = visibleUnits(cols);
      markPages(rows, cols);
      const per = Math.max(1, Math.floor((PRINT.pageW - PRINT.numMM) / PRINT.colMM));
      const ngroups = Math.ceil(cols.length / per);
      const size = Math.ceil(cols.length / ngroups);
      const groups = [];
      for (let i = 0; i < cols.length; i += size) groups.push(cols.slice(i, i + size));
      const baseSel = root.querySelector('[data-k="base"]');
      const baseLabel = baseSel && baseSel.selectedOptions[0] ? baseSel.selectedOptions[0].textContent : "";
      const head = `<div class="print-head" translate="no"><b>${esc(data.title || t("Synopse"))}</b> · ${t("{n} Stellen", { n: rows.length })} · ` +
        (ngroups > 1 ? t("{n} Zeugen in {g} Gruppen (die Gruppen einer Folge von Stellen stehen auf aufeinanderfolgenden Seiten)", { n: cols.length, g: ngroups })
          : t("{n} Zeugen", { n: cols.length })) +
        (baseLabel ? ` · ${t("Vergleich mit: {b}", { b: esc(baseLabel) })}` : "") + `<span class="print-legend">` +
        CLASSES.map(c => `<span><span class="sw ${c.id === "corr" ? "" : "c-" + c.id}" style="${legendStyle(c.id)}">${c.mk}</span>${esc(t(c.label))}</span>`).join("") + `</span></div>`;
      const table = (blk, g, gi) => {
        const first = blk.length ? blk[0].i + 1 : 0, last = blk.length ? blk[blk.length - 1].i + 1 : 0;
        let h = `<table class="syn print-t${state.view.compact ? " compact" : ""}" translate="no"><colgroup><col style="width:${PRINT.numMM}mm">${g.map(() => "<col>").join("")}</colgroup>
          <thead>${ngroups > 1 ? `<tr class="pgrp"><th colspan="${g.length + 1}">${t("Stellen {a}–{b}", { a: first, b: last })} · ${t("Zeugengruppe {a} von {b}", { a: gi + 1, b: ngroups })}</th></tr>` : ""}
          <tr><th class="num">${t("Stelle")}</th>${g.map(c => `<th>${esc(c.label)}${c.ac ? " */ᶜ" : ""}</th>`).join("")}</tr></thead><tbody>`;
        let seg = null;
        for (const { u, i, base } of blk) {
          if (u.seg !== seg) {
            seg = u.seg;
            h += `<tr class="segrow"><td class="num"></td><td colspan="${g.length}">${segLabel(seg)}</td></tr>`;
          }
          const lemIds = u.lem ? (u.readings.find(r => r.id === u.lem) || { wits: [] }).wits : [];
          h += `<tr class="${u.variant ? "var" : "inv"}"><td class="num">${i + 1}${u.lem ? " ●" : ""}${u.transposition ? " ⇄" : ""}${u.link ? " ↔" : ""}${u.inserted ? ` <span class="insmk" title="${esc(t("eingefügte Zeile"))}">+</span>` : ""}${edMarks(u)}</td>` +
            g.map(c => cellHTML(u, c, base, lemIds.includes(c.main))).join("") + "</tr>";
        }
        return h + "</tbody></table>";
      };
      const div = document.createElement("div");
      div.className = "print-syn";
      document.body.appendChild(div);
      let blocks = [rows];
      if (ngroups > 1 && rows.length) {
        // measure the rows at print width (all groups), then fill each page as far as it goes
        div.classList.add("measure");
        div.innerHTML = head + groups.map((g, gi) => table(rows, g, gi)).join("");
        const headH = div.querySelector(".print-head").getBoundingClientRect().height / MM;
        const tables = [...div.querySelectorAll("table")];
        const theadH = Math.max(...tables.map(t => t.tHead.getBoundingClientRect().height)) / MM;
        const bodies = tables.map(t => [...t.tBodies[0].rows]);
        // row heights per unit (a section heading row counts with the unit after it)
        const hts = rows.map(() => 0);
        for (const trs of bodies) {
          let k = -1, extra = 0;
          for (const tr of trs) {
            const h = tr.getBoundingClientRect().height / MM;
            if (tr.classList.contains("segrow")) { extra += h; continue; }
            k++;
            hts[k] = Math.max(hts[k], h + extra);
            extra = 0;
          }
        }
        blocks = [];
        let cur = [], used = 0, cap = PRINT.pageH - headH - theadH - 4;
        rows.forEach((r, k) => {
          if (cur.length && used + hts[k] > cap) { blocks.push(cur); cur = []; used = 0; cap = PRINT.pageH - theadH - 4; }
          cur.push(r); used += hts[k];
        });
        if (cur.length) blocks.push(cur);
        div.classList.remove("measure");
      }
      let html = head;
      blocks.forEach(blk => groups.forEach((g, gi) => { html += table(blk, g, gi); }));
      div.innerHTML = html;
      document.body.classList.add("printing");
    }
    function removePrint() {
      for (const x of document.querySelectorAll(".print-syn")) x.remove();
      document.body.classList.remove("printing");
    }
    if (window.__ptaPrint) {
      window.removeEventListener("beforeprint", window.__ptaPrint[0]);
      window.removeEventListener("afterprint", window.__ptaPrint[1]);
    }
    window.__ptaPrint = [() => { if (root.isConnected && root.offsetParent !== null) buildPrint(); }, removePrint];
    window.addEventListener("beforeprint", window.__ptaPrint[0]);
    window.addEventListener("afterprint", window.__ptaPrint[1]);
    $('[data-k="print"]').onclick = () => { buildPrint(); window.print(); };

    function drawRotated(table, rows, cols) {
      table.className = "syn rot" + (state.view.compact ? " compact" : "");
      rows = rows.slice(0, state.limit);
      let html = `<thead><tr><th class="num"></th>${rows.map(({ u, i }) => `<th data-key="${esc(u.key)}">${i + 1}</th>`).join("")}</tr></thead><tbody>`;
      for (const c of cols) {
        html += `<tr><td class="wl">${esc(c.label)}</td>` + rows.map(({ u, base }) => {
          const td = cellHTML(u, c, base, false);
          return td.replace("<td class=\"", `<td data-key="${esc(u.key)}" class="unitcol${state.selected === u.key ? " selcol" : ""} `);
        }).join("") + "</tr>";
      }
      table.innerHTML = html + "</tbody>";
      for (const td of table.querySelectorAll("[data-key]")) td.onclick = () => select(td.dataset.key, true);
    }

    function select(key, fromClick) {
      state.selected = key;
      for (const tr of root.querySelectorAll("tr.unit.sel")) tr.classList.remove("sel");
      for (const td of root.querySelectorAll(".selcol")) td.classList.remove("selcol");
      let tr = root.querySelector(`tr.unit[data-key="${CSS.escape(key)}"]`);
      if (!tr && !state.rotate) {
        const cols = shownColumns();
        const k = visibleUnits(cols).findIndex(r => r.u.key === key);
        if (k >= state.limit) { state.limit = k + 100; draw(); tr = root.querySelector(`tr.unit[data-key="${CSS.escape(key)}"]`); }
      }
      if (tr) { tr.classList.add("sel"); if (!fromClick) tr.scrollIntoView({ block: "center" }); }
      for (const td of root.querySelectorAll(`td.unitcol[data-key="${CSS.escape(key)}"]`)) td.classList.add("selcol");
      drawGraph(true);
      const u = data.units.find(x => x.key === key);
      if (u && opts.onSelect) opts.onSelect(u, api);
      else if (u) showReadonly(u);
    }

    function showReadonly(u) {
      const d = root.querySelector(".drawer");
      d.classList.remove("hidden");
      const idx = data.units.indexOf(u) + 1;
      const lab = id => (data.witnesses.find(w => w.id === id) || {}).label || id;
      d.innerHTML = `<div class="row" style="justify-content:space-between"><h3>${t("Stelle {n}", { n: idx })}</h3><button class="icon-btn" data-x>${t("Schließen")}</button></div>
        <div class="sub">${segLabel(u.seg)}</div>
        ${u.readings.map(r => `<div class="reading${r.id === u.lem ? " is-lem" : ""}">
          <div class="rt">${r.c ? esc(r.t) : '<span class="empty-sign">om.</span>'}</div>
          <div class="meta"><span class="sig">${esc(r.wits.map(lab).join(" "))}</span>
          ${r.type ? `<span class="tag">${esc(r.type)}</span>` : ""}${r.cause ? `<span class="tag">${esc(r.cause)}</span>` : ""}
          ${r.id === u.lem ? '<span class="tag">Lemma</span>' : ""}</div></div>`).join("")}
        ${u.note ? `<h4>Notiz</h4><p>${esc(u.note)}</p>` : ""}`;
      d.querySelector("[data-x]").onclick = () => d.classList.add("hidden");
    }

    function navigate(step) {
      const cols = shownColumns();
      const rows = visibleUnits(cols).filter(r => r.u.variant);
      if (!rows.length) return;
      let k = rows.findIndex(r => r.u.key === state.selected);
      k = k < 0 ? 0 : Math.min(rows.length - 1, Math.max(0, k + step));
      select(rows[k].u.key, false);
    }

    root.addEventListener("keydown", e => {
      if (e.target.matches("input, textarea, select")) return;
      if (e.key === "j" || e.key === "ArrowDown" && e.altKey) { navigate(1); e.preventDefault(); }
      if (e.key === "k" || e.key === "ArrowUp" && e.altKey) { navigate(-1); e.preventDefault(); }
    });

    const api = {
      draw, select, navigate, state,
      drawer: () => root.querySelector(".drawer"),
      update(newData, keepKey) {
        data = newData; api.data = newData; state.data = newData; tokenCache = null;
        for (const k in tokenFlags) delete tokenFlags[k];
        for (const u of data.units) for (const cid in u.cells) {
          const c = u.cells[cid];
          if ((c.flags || []).includes("unclear")) for (const t of c.tokens || []) tokenFlags[t] = true;
        }
        const scroll = root.querySelector(".syn-scroll").scrollTop;
        draw();
        root.querySelector(".syn-scroll").scrollTop = scroll;
        if (keepKey) {
          // keepKey: a unit key or a list of token ids; find the unit that now holds them
          let key = typeof keepKey === "string" ? keepKey : null;
          if (!key || !data.units.some(u => u.key === key)) {
            const toks = new Set(Array.isArray(keepKey) ? keepKey : [keepKey]);
            let best = null, bestN = 0;
            for (const u of data.units) {
              if (toks.has(u.key)) { best = u; break; }
              let n = 0;
              for (const c of Object.values(u.cells)) for (const t of c.tokens || []) if (toks.has(t)) n++;
              if (n > bestN) { best = u; bestN = n; }
            }
            key = best ? best.key : null;
          }
          if (key) select(key, true);
        }
      },
      data,
    };
    draw();
    if (state.selected) select(state.selected, false);
    return api;
  }

  window.PTASynopsis = {
    create, columns, baseReading, cellClass, CLASSES,
    mountStandalone(root, data) { installTips(document); return create(root, data, { readonly: true }); },
    tip, installTips,
  };
})();
