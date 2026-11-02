/* Variant graph – shared by the application and the stand-alone HTML export.

   Every variation unit is a column. A reading is a node; text shared by all witnesses is a
   single node. Every witness is a path through the graph: an edge joins the readings a
   witness has in consecutive columns. Where a witness has no text (omission) its path runs
   below the nodes as a dashed bypass. Long transpositions are drawn as arcs above the graph
   (dashed while they are only suggested). A reading with sub-variants (units.assign_parents)
   is drawn with its sub-variants directly below it, framed together; the sub-variants are
   marked ↳. Large graphs are drawn in chunks while scrolling. */
(function () {
  "use strict";

  const t = (s, v) => (window.t ? window.t(s, v) : (v ? s.replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? v[k] : m)) : s));
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const NODE_H = 28, ROW_GAP = 14, COL_GAP = 44, TOP = 46, PAD = 24, MAX_W = 240, LANES = 5, LANE_GAP = 9;
  const CHUNK = 80;
  const LABEL_FONT = '10.5px "Source Sans 3", system-ui, sans-serif';

  let ctx2d = null;
  function measure(text, font) {
    if (!ctx2d) ctx2d = document.createElement("canvas").getContext("2d");
    ctx2d.font = font;
    return ctx2d.measureText(text).width;
  }
  function fit(text, font, max) {
    if (measure(text, font) <= max) return text;
    const words = text.split(" ");
    if (words.length > 2) {
      // keep beginning and end: "καὶ πρὶν … γράμματα,"
      for (let k = Math.floor(words.length / 2); k >= 1; k--) {
        const s = words.slice(0, k).join(" ") + " … " + words.slice(-k).join(" ");
        if (measure(s, font) <= max) return s;
      }
    }
    let s = text;
    while (s.length > 2 && measure(s + "…", font) > max) s = s.slice(0, -1);
    return s + "…";
  }

  /**
   * units: list of units (as in the model); wits: [{id, label}]; opts:
   *   baseOf(u) → reading used as reference (colours), mergeOrtho, font
   */
  function layout(units, wits, opts) {
    const font = opts.font || '14px "Gentium Plus", "Noto Serif", serif';
    const ids = wits.map(w => w.id);
    const label = Object.fromEntries(wits.map(w => [w.id, w.label]));
    const cols = [];
    let x = PAD, maxRows = 1;
    for (const u of units) {
      const present = ids.filter(w => w in u.cells);
      const groups = new Map();
      for (const w of present) {
        const c = u.cells[w];
        if (!c.c) continue;                                   // no text: the witness bypasses this column
        const key = opts.mergeOrtho && u.variant ? (c.o || c.c) : c.c;
        if (!groups.has(key)) groups.set(key, { key, text: c.t, wits: [], texts: new Set() });
        const g = groups.get(key);
        g.wits.push(w);
        g.texts.add(c.t);
      }
      let nodes = [...groups.values()].sort((a, b) => b.wits.length - a.wits.length);
      // sub-variants: below their reading, framed together
      const fams = [];
      if (u.variant && (u.readings || []).some(r => r.parent)) {
        const readingOf = n => {
          const rs = (u.readings || []).filter(r => !r.editorial && r.wits.some(w => n.wits.includes(w)));
          return rs.length ? rs : null;
        };
        for (const n of nodes) {
          const rs = readingOf(n) || [];
          n.rids = rs.map(r => r.id);
          const ps = new Set(rs.map(r => r.parent || ""));
          n.parent = ps.size === 1 ? [...ps][0] : "";       // merged orthographic node: only if all agree
          n.sub = rs.find(r => r.parent && r.parent === n.parent) || null;
        }
        const ordered = [];
        for (const n of nodes) {
          if (n.parent) continue;
          ordered.push(n);
          const kids = nodes.filter(k => k.parent && n.rids.includes(k.parent));
          if (kids.length) { fams.push([n, ...kids]); ordered.push(...kids); }
        }
        for (const n of nodes) if (!ordered.includes(n)) { n.parent = ""; ordered.push(n); }
        nodes = ordered;
      }
      const base = u.variant && opts.baseOf ? opts.baseOf(u) : null;
      for (const n of nodes) {
        const full = n.text;
        n.full = n.texts.size > 1 ? [...n.texts].join(" / ") : full;
        n.cls = nodeClass(u, n, base, opts.mergeOrtho);
        n.w = Math.min(MAX_W, Math.max(30, measure(full, font) + 20) + (n.parent ? 14 : 0));
        n.label = (n.parent ? "↳ " : "") + fit(full, font, n.w - 16 - (n.parent ? 14 : 0));
        if (n.parent) {
          const p = nodes.find(k => k.rids && k.rids.includes(n.parent));
          const d = (n.sub && n.sub.sub_diff) || {};
          const what = [d.missing ? t(d.missing === 1 ? "ohne 1 Wort" : "ohne {n} Wörter", { n: d.missing }) : "",
            d.added ? t(d.added === 1 ? "1 Wort mehr" : "{n} Wörter mehr", { n: d.added }) : "",
            d.changed ? t(d.changed === 1 ? "1 Stelle anders" : "{n} Stellen anders", { n: d.changed }) : ""].filter(Boolean).join(", ");
          n.subTip = t("Untervariante von „{p}“", { p: p ? p.text : "" }) + (what ? ` (${what})` : "") + (n.sub && n.sub.sub_warn ? " ⚠" : "");
        }
      }
      // readings of the editor (conjecture, correction, proposition, suspected lacuna): own nodes
      // below, on no witness path
      const KIND = { conjecture: "Konjektur", correction: "Korrektur", proposition: "Vorschlag|proposition", lacunam_indicavit: "Lücke vermutet" };
      for (const r of (u.readings || []).filter(r => r.editorial)) {
        const text = r.t || t("[Lücke]");
        const n = { key: "ed:" + r.editorial.id, text, wits: [], ed: true, cls: "ed" + (r.id === u.lem ? " g-edlem" : "") };
        n.full = text;
        n.tip = `${t(KIND[r.editorial.kind] || "Konjektur")}${r.id === u.lem ? " (" + t("Lemma") + ")" : ""}: ${text}`;
        n.w = Math.min(MAX_W, Math.max(30, measure(text, font) + 20));
        n.label = fit(text, font, n.w - 16);
        nodes.push(n);
      }
      const w = nodes.length ? Math.max(...nodes.map(n => n.w)) : 30;
      nodes.forEach((n, k) => { n.y = TOP + k * (NODE_H + ROW_GAP); n.x = x + (w - n.w) / 2; });
      maxRows = Math.max(maxRows, nodes.length);
      cols.push({ u, x, w, nodes, fams, present: new Set(present) });
      x += w + COL_GAP;
    }
    const rowsBottom = n => TOP + n * (NODE_H + ROW_GAP) + 4;

    // witness paths → aggregated edges
    const nodeOf = cols.map(c => {
      const m = {};
      c.nodes.forEach((n, k) => n.wits.forEach(w => { m[w] = k; }));
      return m;
    });
    const edges = new Map();
    for (const w of ids) {
      let last = null;
      for (let j = 0; j < cols.length; j++) {
        if (!cols[j].present.has(w)) { last = null; continue; }   // lacuna / outside the witness: path ends
        const k = nodeOf[j][w];
        if (k === undefined) continue;                             // omission: bypass
        if (last) {
          const key = `${last[0]}|${last[1]}|${j}|${k}`;
          if (!edges.has(key)) edges.set(key, { a: last[0], na: last[1], b: j, nb: k, wits: [] });
          edges.get(key).wits.push(w);
        }
        last = [j, k];
      }
    }
    const edgeList = [...edges.values()];
    let lane = 0, height = rowsBottom(maxRows) + 20;
    for (const e of edgeList) {
      e.skip = e.b > e.a + 1;
      if (e.skip) {
        // bypass just below the nodes of the columns it passes
        let rows = 1;
        for (let k = e.a; k <= e.b; k++) rows = Math.max(rows, cols[k].nodes.length);
        e.lane = lane++ % LANES;
        e.y = rowsBottom(rows) + e.lane * LANE_GAP;
        height = Math.max(height, e.y + 20);
      }
      const both = ids.filter(w => cols[e.a].present.has(w) && cols[e.b].present.has(w)).length;
      e.full = e.wits.length >= both;
      e.labelText = e.wits.map(w => label[w]).join(" ");
    }
    // long transpositions
    const colOf = new Map(cols.map((c, j) => [c.u.key, j]));
    const arcs = [];
    for (const c of cols) {
      const l = c.u.link || c.u.suggest;
      if (l && l.next && colOf.has(l.next)) arcs.push({ a: colOf.get(c.u.key), b: colOf.get(l.next), suggested: !c.u.link });
    }
    return { cols, edges: edgeList, arcs, width: x - COL_GAP + PAD, height, total: ids.length, label, colOf, font };
  }

  function nodeClass(u, n, base, mergeOrtho) {
    if (!u.variant) return "inv";
    if (!base) return "same";
    const r = u.readings.find(r => r.wits.includes(n.wits[0]));
    if (r && r.type === "transposition") return "transp";
    if (!base.c) return "add";
    if (mergeOrtho ? n.key === (base.o || base.c) : n.key === base.c) return "same";
    if (base.o && u.cells[n.wits[0]].o === base.o) return "ortho";
    return "subst";
  }

  /* ------------------------------------------------------------------ view */
  function Viewer(host, opts) {
    host.innerHTML = `<div class="graph-scroll" tabindex="0" aria-label="Variantengraph"><div class="graph-canvas"></div></div>`;
    const scroller = host.querySelector(".graph-scroll"), canvas = host.querySelector(".graph-canvas");
    let L = null, drawn = new Set(), selected = null, frame = 0;

    function chunkSvg(ci) {
      const from = ci * CHUNK, to = Math.min(L.cols.length, from + CHUNK);
      const x0 = L.cols[from].x - COL_GAP / 2;
      const x1 = to < L.cols.length ? L.cols[to].x - COL_GAP / 2 : L.width;
      const parts = [];
      // selected column
      for (let j = from; j < to; j++) {
        const c = L.cols[j];
        if (c.u.key === selected) parts.push(`<rect class="gsel" x="${c.x - 10}" y="6" width="${c.w + 20}" height="${L.height - 12}" rx="8"/>`);
      }
      // readings with their sub-variants: a frame around them
      for (let j = from; j < to; j++) {
        const c = L.cols[j];
        for (const f of c.fams || []) {
          const y0 = Math.min(...f.map(n => n.y)) - 5, y1 = Math.max(...f.map(n => n.y)) + NODE_H + 5;
          parts.push(`<rect class="gfam" x="${c.x - 6}" y="${y0}" width="${c.w + 12}" height="${y1 - y0}" rx="9"
            data-tip="${esc(t("Lesart mit Untervarianten: im TEI ein lem bzw. rdg mit inneren app"))}"/>`);
        }
      }
      // arcs starting in this chunk
      for (const a of L.arcs) {
        if (a.a < from || a.a >= to) continue;
        const ca = L.cols[a.a], cb = L.cols[a.b];
        const xa = ca.x + ca.w / 2, xb = cb.x + cb.w / 2, top = 8;
        parts.push(`<path class="garc${a.suggested ? " suggested" : ""}" d="M${xa} ${TOP - 4} C${xa} ${top}, ${xb} ${top}, ${xb} ${TOP - 4}"
          data-tip="${esc(t(a.suggested ? "Vorgeschlagene weite Umstellung: Auslassung an der einen, Zusatz an der anderen Stelle" : "Verknüpfte weite Umstellung: Auslassung an der einen, Zusatz an der anderen Stelle"))}"/>`);
      }
      // edges starting in this chunk
      for (const e of L.edges) {
        if (e.a < from || e.a >= to) continue;
        const A = L.cols[e.a].nodes[e.na], B = L.cols[e.b].nodes[e.nb];
        const x1 = A.x + A.w, y1 = A.y + NODE_H / 2, x2 = B.x, y2 = B.y + NODE_H / 2;
        const sw = 1 + 5 * e.wits.length / L.total;
        let d, lx, ly;
        if (!e.skip) {
          const mx = (x1 + x2) / 2;
          d = `M${x1} ${y1} C${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
          lx = mx; ly = (y1 + y2) / 2 - 4;
        } else {
          const yl = e.y;
          d = `M${x1} ${y1} C${x1 + 18} ${y1}, ${x1 + 6} ${yl}, ${x1 + 26} ${yl} L${x2 - 26} ${yl} C${x2 - 6} ${yl}, ${x2 - 18} ${y2}, ${x2} ${y2}`;
          lx = (x1 + x2) / 2; ly = yl - 3;
        }
        const tip = e.skip ? t("Auslassung (Umgehung): {w}", { w: e.labelText }) : e.labelText;
        parts.push(`<path class="gedge${e.skip ? " skip" : ""}${e.full ? " full" : ""}" d="${d}" stroke-width="${sw.toFixed(1)}" data-tip="${esc(tip)}"/>`);
        if (!e.full) {
          // label only where it fits; the full list of sigla is always in the tooltip
          const room = e.skip ? (x2 - x1 - 60) : (x2 - x1 - 6);
          let short = e.wits.length <= 3 ? e.labelText : t("{n} Hss.", { n: e.wits.length });
          if (measure(short, LABEL_FONT) > room) short = measure(`${e.wits.length}`, LABEL_FONT) <= room ? `${e.wits.length}` : "";
          if (short) parts.push(`<text class="glabel" x="${lx}" y="${ly}" text-anchor="middle" data-tip="${esc(tip)}">${esc(short)}</text>`);
        }
      }
      // nodes
      for (let j = from; j < to; j++) {
        const c = L.cols[j];
        for (const n of c.nodes) {
          const sig = n.wits.map(w => L.label[w]).join(" ");
          const tip = n.tip || (c.u.variant ? `${n.full}\n${sig}${n.subTip ? "\n" + n.subTip : ""}` : `${n.full}\n(${t("alle Zeugen")})`);
          parts.push(`<g class="gnode g-${n.cls}${n.parent ? " g-sub" : ""}" data-key="${esc(c.u.key)}" data-tip="${esc(tip)}">
            <rect x="${n.x}" y="${n.y}" width="${n.w}" height="${NODE_H}" rx="6"/>
            <text x="${n.x + n.w / 2}" y="${n.y + NODE_H / 2 + 5}" text-anchor="middle">${esc(n.label)}</text></g>`);
        }
      }
      return `<svg class="gchunk" style="left:${x0}px" width="${x1 - x0}" height="${L.height}" viewBox="${x0} 0 ${x1 - x0} ${L.height}">${parts.join("")}</svg>`;
    }

    function renderVisible() {
      frame = 0;
      if (!L || !L.cols.length) return;
      const left = scroller.scrollLeft - scroller.clientWidth, right = scroller.scrollLeft + 2 * scroller.clientWidth;
      const nChunks = Math.ceil(L.cols.length / CHUNK);
      let html = "";
      for (let ci = 0; ci < nChunks; ci++) {
        if (drawn.has(ci)) continue;
        const from = L.cols[ci * CHUNK].x, to = L.cols[Math.min(L.cols.length, (ci + 1) * CHUNK) - 1];
        if (to.x + to.w < left || from > right) continue;
        drawn.add(ci);
        html += chunkSvg(ci);
      }
      if (html) canvas.insertAdjacentHTML("beforeend", html);
    }
    scroller.addEventListener("scroll", () => { if (!frame) frame = requestAnimationFrame(renderVisible); }, { passive: true });
    canvas.addEventListener("click", e => {
      const g = e.target.closest(".gnode");
      if (g && opts.onSelect) opts.onSelect(g.dataset.key);
    });

    return {
      show(layoutObj, selKey, center) {
        L = layoutObj; selected = selKey; drawn = new Set();
        canvas.innerHTML = "";
        canvas.style.width = L.width + "px";
        canvas.style.height = L.height + "px";
        if (!L.cols.length) { canvas.innerHTML = `<p class="muted" style="padding:12px">${t("Keine Stellen in dieser Auswahl.")}</p>`; return; }
        if (center && selKey != null && L.colOf.has(selKey)) {
          const c = L.cols[L.colOf.get(selKey)];
          scroller.scrollLeft = Math.max(0, c.x + c.w / 2 - scroller.clientWidth / 2);
        }
        renderVisible();
      },
      select(selKey, center) {
        if (!L) return;
        this.show(L, selKey, center);
      },
    };
  }

  window.PTAGraph = { layout, Viewer };
})();
