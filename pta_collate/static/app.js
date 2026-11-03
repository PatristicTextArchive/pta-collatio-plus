/* PTA Collatio+ – application logic (preparation, synopsis editing, export). */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  let st = null;          // server state
  let infos = {};         // witness metadata
  let model = null;       // current units
  let syn = null;         // synopsis api

  const TYPES = ["", "omission", "addition", "transposition", "deletion", "illegible", "damage", "fenestra", "correction", "conjecture"];
  const TYPE_LABEL = { "": "kein Typ", omission: "Auslassung", addition: "Hinzufügung", transposition: "Umstellung", deletion: "Tilgung",
    illegible: "unleserlich", damage: "Beschädigung", fenestra: "Fenestra", correction: "Korrektur", conjecture: "Konjektur" };
  const CAUSES = ["", "orthographic", "homoioteleuton", "homoiarkton", "saut_du_meme", "dittography"];
  const CAUSE_LABEL = { "": "keine Ursache", orthographic: "orthographisch", homoioteleuton: "Homoioteleuton", homoiarkton: "Homoiarkton",
    saut_du_meme: "saut du même", dittography: "Dittographie" };
  const NORM = [
    ["ignore_punctuation", "Interpunktion ignorieren",
      "An: Lesarten, die sich nur in der Interpunktion unterscheiden (γράμματα, / γράμματα·), gelten als gleich; reine Satzzeichen werden nicht kollationiert. Aus: Satzzeichen werden mitkollationiert, solche Unterschiede erscheinen als Varianten (gruppiert mit der Lesart, aber ohne cause=orthographic)."],
    ["lowercase", "Groß-/Kleinschreibung beim Ausrichten ignorieren", "Καί und καί werden beim Ausrichten als gleich behandelt."],
    ["accents", "Akzente ignorieren", "καὶ und καί, τῷ und τῶ werden beim Ausrichten als gleich behandelt."],
    ["breathings", "Spiritus ignorieren", "ὁ und ο, ἐν und εν werden beim Ausrichten als gleich behandelt."],
    ["iota_subscript", "Iota subscriptum ignorieren", "τῷ und τω werden beim Ausrichten als gleich behandelt."],
    ["final_sigma", "ς und σ gleichsetzen", "Wichtig, wenn Transkriptionen am Wortende teils σ, teils ς schreiben."],
    ["nu_ephelkystikon", "ν ephelkystikon ignorieren", "εἶπεν = εἶπε, ἐστίν = ἐστί (nicht bei οὐδέν, μέν, ἐν usw.)."],
    ["elision", "Elisionszeichen ignorieren", "Der Apostroph wird beim Ausrichten nicht berücksichtigt: δ’ wird zu δ (nicht zu δέ ergänzt)."],
    ["itacism_in_alignment", "Itazismus (ει/ι/η/οι/υ, αι/ε, ο/ω) und Doppelkonsonanten schon beim Ausrichten gleichsetzen",
      "Hilft bei stark itazistisch schreibenden Handschriften. Die Varianten bleiben sichtbar und werden als orthographisch eingestuft."],
    ["readings_ignore_case", "Lesarten, die sich nur in Groß-/Kleinschreibung unterscheiden, nicht als Variante werten",
      "Betrifft nicht das Ausrichten, sondern ob eine Variationsstelle entsteht: Καί / καί ergibt dann keine."],
    ["readings_ignore_accents", "Lesarten, die sich nur in Akzenten/Spiritus unterscheiden, nicht als Variante werten",
      "Wie oben für Akzente und Spiritus: τῷ / τῶ ergibt dann keine Variationsstelle."],
  ];
  const tip = t => PTASynopsis.tip(t);

  /* ------------------------------------------------------------ helpers */
  async function api(method, url, body) {
    const res = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.detail || res.statusText);
    return data;
  }
  function toast(msg, err) {
    const t = document.createElement("div");
    t.className = "toast" + (err ? " err" : "");
    t.setAttribute("role", "status");
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), err ? 6000 : 2600);
  }
  async function busy(msg, fn) {
    const b = document.createElement("div");
    b.className = "busy";
    b.textContent = msg;
    document.body.appendChild(b);
    try { return await fn(); } catch (e) { toast(e.message, true); throw e; } finally { b.remove(); }
  }
  const getPath = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
  function setPath(o, p, v) { const ks = p.split("."); let a = o; ks.slice(0, -1).forEach(k => { a[k] = a[k] || {}; a = a[k]; }); a[ks.at(-1)] = v; }

  // After saving, keep the local project object: the form handlers hold references to it.
  // Only the server's status fields (stale, path, …) are taken over.
  function keepProject(res) { const proj = st.project; st = res; st.project = proj; }

  let putTimer = null, putKeys = new Set();
  function queuePut(key) {
    putKeys.add(key);
    clearTimeout(putTimer);
    putTimer = setTimeout(async () => {
      const body = {};
      for (const k of putKeys) body[k] = st.project[k];
      putKeys.clear();
      try { keepProject(await api("PUT", "/api/project", body)); renderStatus(); if (body.units && model) { model = await api("GET", "/api/model"); if (syn) syn.update(model, syn.state.selected); } }
      catch (e) { toast(e.message, true); }
    }, 350);
  }

  function renderStatus() {
    const s = $("#status");
    $("#proj-name").textContent = st.project.title ? "· " + st.project.title : "";
    if (!st.path) { s.textContent = "Projekt noch nicht gespeichert"; s.className = "status warn"; }
    else if (st.stale) { s.textContent = "Einstellungen geändert – Kollation neu starten"; s.className = "status warn"; }
    else { s.textContent = st.path; s.className = "status"; s.title = st.path; }
    const ri = st.result_info;
    $("#run-info").textContent = ri ? `Letzter Lauf ${ri.created.replace("T", " ")} (${ri.seconds} s)` : "";
  }

  /* -------------------------------------------------------------- views */
  function show(view) {
    for (const v of ["prep", "syn", "exp", "var", "about"]) $("#view-" + v).hidden = v !== view;
    document.body.dataset.view = view;
    for (const a of $$("[data-view-link]")) {
      if (a.dataset.viewLink === view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    }
    for (const b of $$(".steps button")) {
      if (b.dataset.view === view) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    }
    if (location.hash !== "#" + view) history.replaceState(null, "", "#" + view);
    if (view === "prep" && !prepReady) { prepReady = true; loadInfos().then(renderPrep).catch(e => toast(e.message, true)); }
    if (view === "syn") renderSynopsis();
    if (view === "exp") renderExport();
    if (view === "var") renderVariance(false);
  }
  let prepReady = false;
  for (const b of $$(".steps button")) b.onclick = () => show(b.dataset.view);
  for (const a of $$("[data-view-link]")) a.onclick = e => { e.preventDefault(); show(a.dataset.viewLink); window.scrollTo(0, 0); };

  /* -------------------------------------------------------- preparation */
  function renderPrep() {
    const p = st.project;
    $("#proj-path").value = st.path || "";
    for (const el of $$("[data-p]")) el.value = getPath(p, el.dataset.p) ?? "";
    renderWitnesses();
    renderSegments();
    renderNorm();
    renderAligner();
    renderSources();
    $("#join-breaks").checked = !!p.join_suspicious_breaks;
    $("#split-fused").checked = !!p.split_fused_words;
    for (const el of $$("[data-u]")) {
      const v = p.units[el.dataset.u];
      if (el.type === "checkbox") el.checked = !!v; else el.value = v;
    }
    renderStatus();
  }

  function renderSources() {
    const list = st.project.sources = st.project.sources || [];
    $("#src-body").innerHTML = list.length ? list.map((x, i) => `<tr>
      <td><input type="text" data-s="id" data-i="${i}" value="${esc(x.id)}" size="8"></td>
      <td><input type="text" data-s="name" data-i="${i}" value="${esc(x.name || "")}"></td>
      <td><select data-s="kind" data-i="${i}"><option value="person" ${x.kind !== "bibl" ? "selected" : ""}>Person</option><option value="bibl" ${x.kind === "bibl" ? "selected" : ""}>Edition</option></select></td>
      <td><input type="text" data-s="ref" data-i="${i}" value="${esc(x.ref || "")}" placeholder="https://d-nb.info/gnd/…"></td>
      <td><button class="icon-btn" data-sdel="${i}">Entfernen</button></td></tr>`).join("")
      : `<tr><td colspan="5" class="muted">Noch keine. Eigene Konjekturen brauchen keinen Eintrag.</td></tr>`;
    for (const el of $$("[data-s]")) el.onchange = () => {
      const x = list[+el.dataset.i], v = el.value.trim();
      if (el.dataset.s === "id" && !/^[A-Za-z_][\w.-]*$/.test(v)) { toast("Kürzel: Buchstaben, Ziffern, _ - . (für xml:id), beginnend mit einem Buchstaben.", true); el.value = x.id; return; }
      x[el.dataset.s] = v; queuePut("sources");
    };
    for (const b of $$("[data-sdel]")) b.onclick = () => { list.splice(+b.dataset.sdel, 1); queuePut("sources"); renderSources(); };
  }
  $("#src-add").onclick = () => {
    const list = st.project.sources = st.project.sources || [];
    let n = list.length + 1; while (list.some(x => x.id === "Ed" + n)) n++;
    list.push({ id: "Ed" + n, name: "", kind: "person" }); queuePut("sources"); renderSources();
  };

  for (const el of $$("[data-p]")) el.onchange = () => {
    const key = el.dataset.p.split(".")[0];
    setPath(st.project, el.dataset.p, el.value);
    queuePut(key);
  };
  for (const el of $$("[data-u]")) el.onchange = () => {
    st.project.units[el.dataset.u] = el.type === "checkbox" ? el.checked : Number(el.value);
    queuePut("units");
  };

  function renderWitnesses() {
    const tb = $("#wit-body");
    const ws = st.project.witnesses;
    if (!ws.length) { tb.innerHTML = `<tr><td colspan="7" class="muted">Noch keine Transkriptionen. Fügen Sie einen Ordner oder einzelne Dateien hinzu.</td></tr>`; }
    else tb.innerHTML = ws.map((w, i) => {
      const inf = infos[w.id] || {};
      return `<tr class="${w.include ? "" : "off"}" data-i="${i}">
        <td><button class="icon-btn" data-up title="nach oben" aria-label="nach oben">▲</button><button class="icon-btn" data-down title="nach unten" aria-label="nach unten">▼</button></td>
        <td><input type="checkbox" data-inc ${w.include ? "checked" : ""} aria-label="kollationieren"></td>
        <td><input type="text" class="sig" data-sig value="${esc(w.siglum || w.id)}" aria-label="Sigle"></td>
        <td>${esc(inf.name || w.id)}<div class="file">${esc(w.file)}</div></td>
        <td>${inf.has_corrections ? `<select data-lay><option value="both">beide (* und ᶜ)</option><option value="pc">nur post correctionem</option><option value="ac">nur ante correctionem</option></select>` : '<span class="muted">keine</span>'}</td>
        <td><input type="radio" name="sw" data-sw ${st.project.structure_witness === w.id ? "checked" : ""} aria-label="Strukturgeber"></td>
        <td><button class="icon-btn" data-del title="entfernen">Entfernen</button></td></tr>`;
    }).join("");
    for (const tr of $$("tr[data-i]", tb)) {
      const i = +tr.dataset.i, w = ws[i];
      const lay = $("[data-lay]", tr); if (lay) lay.value = w.layers || "both";
      $("[data-inc]", tr).onchange = e => { w.include = e.target.checked; queuePut("witnesses"); renderWitnesses(); };
      $("[data-sig]", tr).onchange = e => { w.siglum = e.target.value.trim() || w.id; queuePut("witnesses"); };
      if (lay) lay.onchange = e => { w.layers = e.target.value; queuePut("witnesses"); refreshPreview(); };
      $("[data-sw]", tr).onchange = () => { st.project.structure_witness = w.id; queuePut("structure_witness"); };
      $("[data-del]", tr).onclick = () => { ws.splice(i, 1); queuePut("witnesses"); renderWitnesses(); renderPreviewSelect(); };
      $("[data-up]", tr).onclick = () => { if (i > 0) { [ws[i - 1], ws[i]] = [ws[i], ws[i - 1]]; queuePut("witnesses"); renderWitnesses(); } };
      $("[data-down]", tr).onclick = () => { if (i < ws.length - 1) { [ws[i + 1], ws[i]] = [ws[i], ws[i + 1]]; queuePut("witnesses"); renderWitnesses(); } };
    }
    renderPreviewSelect();
  }

  function renderSegments() {
    const modes = new Set(["auto", "none"]);
    const keysByMode = {};
    for (const w of st.project.witnesses) {
      const inf = infos[w.id]; if (!inf || !inf.segments) continue;
      for (const [m, keys] of Object.entries(inf.segments)) { modes.add(m); keysByMode[m] = keysByMode[m] || []; for (const k of keys) if (!keysByMode[m].includes(k)) keysByMode[m].push(k); }
    }
    const label = m => m === "auto" ? "automatisch" : m === "none" ? "keine (ganzer Text)" : m === "div" ? "Textteile (div)" : "Meilensteine: " + m.split(":")[1];
    const sel = $("#seg-mode");
    sel.innerHTML = [...modes].map(m => `<option value="${esc(m)}">${esc(label(m))}</option>`).join("");
    sel.value = st.project.segmentation.mode || "auto";
    sel.onchange = () => { st.project.segmentation = { mode: sel.value }; st.project.segments = []; queuePut("segmentation"); queuePut("segments"); renderSegments(); refreshPreview(); };
    let mode = sel.value;
    if (mode === "auto") mode = Object.keys(keysByMode).find(m => m.startsWith("milestone:")) || (keysByMode.div ? "div" : "none");
    const keys = mode === "none" ? [] : ["0", ...(keysByMode[mode] || [])];
    const chosen = new Set(st.project.segments || []);
    $("#seg-list").innerHTML = keys.length ? keys.map(k => `<label class="check"><input type="checkbox" value="${esc(k)}" ${!chosen.size || chosen.has(k) ? "checked" : ""}> ${k === "0" ? "Titel / Vorspann (Text vor dem ersten Abschnittsanker)" : esc(k)}</label>`).join("") +
      `<span class="muted" style="font-size:13px">Abwählen beschränkt die Kollation auf einzelne Abschnitte.</span>` : `<span class="muted">Der ganze Text wird in einem Stück kollationiert.</span>`;
    for (const cb of $$("#seg-list input")) cb.onchange = () => {
      const all = $$("#seg-list input"); const on = all.filter(x => x.checked).map(x => x.value);
      st.project.segments = on.length === all.length ? [] : on; queuePut("segments"); renderPreviewSegs();
    };
    renderPreviewSegs(keys);
  }

  function renderNorm() {
    const n = st.project.normalization;
    $("#norm-preset").value = st.presets[n.preset] ? n.preset : "eigene";
    $("#norm-checks").innerHTML = NORM.map(([k, l, h]) => `<label class="check"><input type="checkbox" data-n="${k}" ${(n[k] ?? (k === "ignore_punctuation")) ? "checked" : ""}> <span>${l}${tip(h)}</span></label>`).join("");
    for (const cb of $$("[data-n]")) cb.onchange = () => { n[cb.dataset.n] = cb.checked; n.preset = "eigene"; $("#norm-preset").value = "eigene"; queuePut("normalization"); refreshPreview(); };
    $("#norm-preset").onchange = e => {
      if (e.target.value === "eigene") return;
      const pre = st.presets[e.target.value]; Object.assign(n, JSON.parse(JSON.stringify(pre)), { preset: e.target.value });
      queuePut("normalization"); renderNorm(); refreshPreview();
    };
    const rules = n.custom || (n.custom = []);
    $("#norm-rules").innerHTML = rules.map((r, i) => `<div class="rule" data-i="${i}"><input type="text" value="${esc(r[0])}" aria-label="Muster" placeholder="Muster, z. B. ^και$"><input type="text" value="${esc(r[1])}" aria-label="Ersetzung" placeholder="Ersetzung"><button class="icon-btn" data-x>Entfernen</button></div>`).join("");
    for (const row of $$("#norm-rules .rule")) {
      const i = +row.dataset.i; const [a, b] = $$("input", row);
      a.onchange = () => { rules[i][0] = a.value; queuePut("normalization"); refreshPreview(); };
      b.onchange = () => { rules[i][1] = b.value; queuePut("normalization"); refreshPreview(); };
      $("[data-x]", row).onclick = () => { rules.splice(i, 1); queuePut("normalization"); renderNorm(); refreshPreview(); };
    }
  }
  $("#rule-add").onclick = () => { st.project.normalization.custom.push(["", ""]); renderNorm(); };

  /* transcription check */
  $("#check-run").onclick = async () => {
    const res = await busy("Transkriptionen werden geprüft …", () => api("POST", "/api/check"));
    const br = res.breaks || [], fu = res.fused || [], mx = res.mixed || [];
    $("#check-info").textContent = (br.length || fu.length || mx.length)
      ? `${br.length} getrennte, ${fu.length} zusammengeschriebene Wörter, ${mx.length} mit lateinischen Buchstaben`
      : "Keine Auffälligkeiten gefunden.";
    const file = f => `<td class="f" title="${esc(f)}">${esc((f || "").split(/[\\/]/).pop())}</td>`;
    // line(s) in the XML file; empty if the word could not be found there as written (e.g. expanded nomina sacra)
    const lines = x => `<td class="f">${esc((x.lines || []).join(", "))}</td>`;
    const section = (title, help, head, rows) => rows.length ? `<h4 class="check-h">${title}${tip(help)}</h4>
      <div class="preview-wrap" style="max-height:240px"><table class="preview"><thead><tr>${head.map(h => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>` : "";
    $("#check-out").innerHTML =
      section("Getrennte Wörter (fehlendes break=\"no\")",
        "Zwei aufeinanderfolgende Wörter, zwischen denen ein einfaches <lb/>, <cb/> oder <pb/> steht, ergeben zusammen ein Wort, das andere Zeugen als ein Wort haben, z. B. καταλαμ <lb/> βάνει. Zeile = Zeile in der XML-Datei.",
        ["Zeuge", "Zeile", "Getrennt", "Vorschlag", "Datei"],
        br.map(b => `<tr><td class="f">${esc(b.wit)}</td><td class="f">${b.line}</td><td>${esc(b.a)} | ${esc(b.b)}</td><td>${esc(b.joined)}</td>${file(b.file)}</tr>`)) +
      section("Zusammengeschriebene Wörter (fehlender Wortzwischenraum)",
        "Das Wort wird mit seinen Nachbarwörtern an derselben Stelle mit den anderen Handschriften verglichen: Haben sie dort zwei (oder drei) Wörter, die zusammen dieses Wort ergeben (σωτῆροςἑρμηνεία → σωτῆρος ἑρμηνεία), wird es gemeldet, sofern mehr Handschriften trennen als ebenso zusammenschreiben und entweder mindestens ein Viertel der übrigen Handschriften trennt oder das Wort selbst ein Indiz trägt (zwei Akzente, Spiritus im Wortinneren, Interpunktion zwischen Buchstaben). Jeder Teil wird für sich normalisiert, ein ν ephelkystikon oder ein Tippfehler im entfernteren Teil stört also nicht. Ohne Indiz sind es oft zusammengeschriebene Proklitika (διατοῦτο, ἐξαυτοῦ), die man auch so belassen kann. Zeile = Zeile in der XML-Datei (bei mehreren gleichen Wörtern auf der Seite alle).",
        ["Zeuge", "Seite", "Zeile", "Wort", "Vorschlag", "Umfeld", "Hss.", "Indiz", "Datei"],
        fu.map(f => `<tr><td class="f">${esc(f.wit)}</td><td class="f">${esc(f.page || "")}</td>${lines(f)}<td>${esc(f.word)}</td><td>${esc(f.split)}</td>
          <td class="ctx">${esc(f.context || "")}</td>
          <td class="f" data-tip="${esc(f.support && f.support.length ? "Trennen hier: " + f.support.join(", ") + (f.same && f.same.length ? " · ebenso zusammengeschrieben: " + f.same.join(", ") : "") : "Anzahl der Handschriften mit dieser Wortfolge im ganzen Text")}">${f.count}${f.same && f.same.length ? ` <span class="muted">/ ${f.same.length}</span>` : ""}</td>
          <td class="f">${esc((f.evidence || []).join(", "))}</td>${file(f.file)}</tr>`)) +
      section("Lateinische Buchstaben in griechischen Wörtern",
        "Lateinische Zeichen, die wie griechische aussehen (K statt Κ, o statt ο). Für das Ausrichten werden sie schon gleichgesetzt; in der Transkription sollten sie korrigiert werden. Zeile = Zeile in der XML-Datei.",
        ["Zeuge", "Seite", "Zeile", "Wort", "lateinisch", "Datei"],
        mx.map(m => `<tr><td class="f">${esc(m.wit)}</td><td class="f">${esc(m.page || "")}</td>${lines(m)}<td>${esc(m.word)}</td><td class="f">${esc(m.latin)}</td>${file(m.file)}</tr>`));
  };
  $("#split-fused").onchange = e => { st.project.split_fused_words = e.target.checked; queuePut("split_fused_words"); };
  $("#join-breaks").onchange = e => { st.project.join_suspicious_breaks = e.target.checked; queuePut("join_suspicious_breaks"); };

  function renderAligner() {
    const a = st.project.aligner;
    const sel = $("#al-engine");
    sel.innerHTML = Object.entries(st.aligners).map(([k, l]) => `<option value="${k}">${esc(l)}</option>`).join("");
    sel.value = a.engine || "builtin";
    for (const el of $$(".eng-builtin")) el.hidden = sel.value !== "builtin";
    for (const el of $$(".eng-collatex")) el.hidden = sel.value !== "collatex";
    for (const el of $$("[data-a]")) {
      const v = a[el.dataset.a];
      if (el.type === "checkbox") el.checked = v !== false; else el.value = v ?? "";
      el.onchange = () => { a[el.dataset.a] = el.type === "checkbox" ? el.checked : el.type === "number" ? Number(el.value) : el.value; queuePut("aligner"); };
    }
    sel.onchange = () => { a.engine = sel.value; queuePut("aligner"); renderAligner(); };
    $("#al-note").textContent = sel.value === "collatex"
      ? (st.collatex.available ? "CollateX läuft über Java und ist bei vielen Zeugen deutlich langsamer." : "CollateX ist nicht verfügbar: " + st.collatex.message)
      : "Läuft ohne Java. Verankert eindeutige Wortfolgen (wie Dekker) und richtet dazwischen mit unscharfem Wortvergleich aus.";
    if (sel.value === "collatex") { a.algorithm = "dekker"; a.comparator = "equality"; }
  }

  /* preview */
  function renderPreviewSelect() {
    const sel = $("#pv-wit"); const cur = sel.value;
    sel.innerHTML = st.project.witnesses.map(w => `<option value="${esc(w.id)}">${esc(w.siglum || w.id)}</option>`).join("");
    if (cur && st.project.witnesses.some(w => w.id === cur)) sel.value = cur;
    refreshPreview();
  }
  function renderPreviewSegs(keys) {
    const sel = $("#pv-seg"); const cur = sel.value;
    if (keys) sel.innerHTML = `<option value="">alle</option>` + keys.map(k => `<option value="${esc(k)}">${k === "0" ? "Titel / Vorspann" : esc(k)}</option>`).join("");
    if ([...sel.options].some(o => o.value === cur)) sel.value = cur;
  }
  $("#pv-wit").onchange = () => refreshPreview();
  $("#pv-seg").onchange = () => refreshPreview();
  let pvTimer;
  function refreshPreview() {
    clearTimeout(pvTimer);
    if ($("#view-prep").hidden) return;
    pvTimer = setTimeout(async () => {
      const id = $("#pv-wit").value;
      if (!id) { $("#pv-out").innerHTML = '<p class="muted" style="padding:10px">Noch keine Zeugen.</p>'; return; }
      try {
        const res = await api("POST", "/api/preview", { id, segment: $("#pv-seg").value, normalization: st.project.normalization,
          segmentation: st.project.segmentation, nomina_sacra: st.project.nomina_sacra, limit: 300 });
        const layers = Object.entries(res.layers);
        if (layers.length === 1) {
          const [, toks] = layers[0];
          $("#pv-out").innerHTML = `<table class="preview"><thead><tr><th>Original${tip("Wort wie transkribiert; Nomina sacra aufgelöst, Wortteile über break=no verbunden.")}</th><th>Vergleich${tip("Vergleichsform: daran wird entschieden, ob zwei Lesarten gleich sind (je nach Einstellung ohne Interpunktion, Groß-/Kleinschreibung, Akzente).")}</th><th>Normalisiert${tip("Form, die der Aligner vergleicht, nach den Regeln unter Normalisierung.")}</th><th>Merkmale${tip("corr: Korrektur, nomSac: Nomen sacrum, unclear: unsicher gelesen, g:diple usw.: Zeichen am Rand; dazu die Seite.")}</th></tr></thead><tbody>` +
            toks.map(t => `<tr title="orthographischer Schlüssel: ${esc(t.o)}"${t.c ? "" : ' class="muted"'}><td class="t">${esc(t.t)}</td><td>${esc(t.c)}</td><td>${esc(t.n)}</td><td class="f">${esc((t.flags || []).join(", "))} ${esc(t.page || "")}</td></tr>`).join("") + "</tbody></table>";
        } else {
          const [[, ac], [, pc]] = layers;
          const n = Math.max(ac.length, pc.length);
          let rows = "";
          for (let i = 0; i < n; i++) {
            const a = ac[i] || {}, b = pc[i] || {};
            rows += `<tr title="orthographischer Schlüssel: ${esc(b.o)}" class="${a.t !== b.t ? "diff" : ""}"><td class="t">${esc(a.t)}</td><td class="t">${esc(b.t)}</td><td>${esc(b.n)}</td><td class="f">${esc((b.flags || []).join(", "))} ${esc(b.page || "")}</td></tr>`;
          }
          $("#pv-out").innerHTML = `<table class="preview"><thead><tr><th>ante corr. (*)${tip("Text vor der Korrektur: del wird gelesen, add nicht.")}</th><th>post corr. (ᶜ)${tip("Text nach der Korrektur: add wird gelesen, del nicht. Gelb: Zeilen, in denen sich beide Schichten unterscheiden.")}</th><th>Normalisiert (ᶜ)${tip("Form, die der Aligner vergleicht, nach den Regeln unter Normalisierung.")}</th><th>Merkmale${tip("corr: Korrektur, nomSac: Nomen sacrum, unclear: unsicher gelesen, g:diple usw.: Zeichen am Rand; dazu die Seite.")}</th></tr></thead><tbody>${rows}</tbody></table>`;
        }
      } catch (e) { $("#pv-out").innerHTML = `<p class="valid-bad" style="padding:10px">${esc(e.message)}</p>`; }
    }, 250);
  }

  /* project buttons */
  $("#proj-open").onclick = async () => {
    const path = $("#proj-path").value.trim(); if (!path) return toast("Bitte den Pfad zur Projektdatei angeben.", true);
    st = await busy("Projekt wird geöffnet …", () => api("POST", "/api/project/open", { path }));
    await loadInfos(); renderPrep(); prepReady = true; model = st.has_result ? await api("GET", "/api/model") : null; syn = null;
    toast("Projekt geöffnet");
  };
  $("#proj-new").onclick = async () => {
    if (!confirm(t("Neues, leeres Projekt beginnen? Nicht gespeicherte Änderungen gehen verloren."))) return;
    st = await api("POST", "/api/project/new", { path: $("#proj-path").value.trim() || null });
    infos = {}; model = null; syn = null; renderPrep();
  };
  $("#save-btn").onclick = async () => {
    let path = st.path;
    // default: next to the transcriptions, i.e. in the repository of the edition
    if (!path) { path = prompt(t("Projektdatei speichern unter:"), ($("#proj-path").value.trim() || st.suggested_path || st.cwd + "/kollation.pta.json")); if (!path) return; }
    st = await api("POST", "/api/project/save", { path }); renderStatus(); $("#proj-path").value = st.path; toast("Projekt gespeichert: " + st.path);
  };
  $("#proj-browse").onclick = () => browse("project");
  $("#wit-add").onclick = () => browse("witnesses");

  /* file browser */
  async function browse(mode) {
    const box = document.createElement("div");
    box.className = "browser";
    box.innerHTML = `<div class="box" role="dialog" aria-modal="true" aria-label="Dateien auswählen">
      <header><input type="text" aria-label="Ordner"><button class="btn" data-go>Öffnen</button></header>
      <div class="list"></div>
      <footer><span class="muted" style="flex:1;align-self:center" data-hint></span><button class="btn" data-cancel>Abbrechen</button>
      <button class="btn primary" data-ok>${mode === "project" ? "Projekt öffnen" : "Ausgewählte hinzufügen"}</button></footer></div>`;
    document.body.appendChild(box);
    const input = $("header input", box);
    let current = st.path ? st.path.replace(/[\\/][^\\/]*$/, "") : (st.project.witnesses[0] ? st.project.witnesses[0].file.replace(/[\\/][^\\/]*$/, "") : st.cwd);
    async function go(path) {
      try {
        const res = await api("GET", "/api/fs?path=" + encodeURIComponent(path));
        current = res.path; input.value = res.path;
        const files = res.files.filter(f => mode === "project" ? f.endsWith(".pta.json") : f.endsWith(".xml") && !f.includes("__cts__"));
        $(".list", box).innerHTML = `<div><a data-dir="${esc(res.parent)}">↰ übergeordneter Ordner</a></div>` +
          res.dirs.map(d => `<div><a data-dir="${esc(res.path + "/" + d)}">${esc(d)}/</a></div>`).join("") +
          files.map(f => mode === "project" ? `<div><label class="check"><input type="radio" name="pf" value="${esc(res.path + "/" + f)}"> ${esc(f)}</label></div>`
            : `<div><label class="check"><input type="checkbox" value="${esc(res.path + "/" + f)}" ${/pta-Ms/.test(f) ? "checked" : ""}> ${esc(f)}</label></div>`).join("");
        $("[data-hint]", box).textContent = mode === "project" ? "" : "Handschriften-Transkriptionen (…pta-Ms….xml) sind vorausgewählt.";
        for (const a of $$("[data-dir]", box)) a.onclick = () => go(a.dataset.dir);
      } catch (e) { toast(e.message, true); }
    }
    $("[data-go]", box).onclick = () => go(input.value);
    input.onkeydown = e => { if (e.key === "Enter") go(input.value); };
    $("[data-cancel]", box).onclick = () => box.remove();
    box.addEventListener("keydown", e => { if (e.key === "Escape") box.remove(); });
    $("[data-ok]", box).onclick = async () => {
      if (mode === "project") {
        const pick = $("input[name=pf]:checked", box); if (!pick) return toast("Bitte eine Projektdatei wählen.", true);
        $("#proj-path").value = pick.value; box.remove(); $("#proj-open").click(); return;
      }
      const paths = $$("input[type=checkbox]:checked", box).map(x => x.value);
      if (!paths.length) return toast("Keine Datei ausgewählt.", true);
      box.remove();
      st = await busy("Transkriptionen werden gelesen …", () => api("POST", "/api/witnesses/add", { paths }));
      await loadInfos(); renderPrep();
      toast(st.skipped.length ? t("{a} Zeugen hinzugefügt, {b} übersprungen (keine Handschrift)", { a: st.added.length, b: st.skipped.length })
        : t("{a} Zeugen hinzugefügt", { a: st.added.length }));
    };
    go(current);
    input.focus();
  }

  async function loadInfos() { infos = st.project.witnesses.length ? await api("GET", "/api/witnesses/info") : {}; }

  $("#run").onclick = async () => {
    if (st.project.witnesses.filter(w => w.include).length < 2) return toast("Bitte mindestens zwei Zeugen auswählen.", true);
    clearTimeout(putTimer);
    if (putKeys.size) { const body = {}; for (const k of putKeys) body[k] = st.project[k]; putKeys.clear(); keepProject(await api("PUT", "/api/project", body)); }
    model = await busy("Kollation läuft …", () => api("POST", "/api/collate"));
    st = await api("GET", "/api/state"); renderStatus(); syn = null;
    toast(`Kollation fertig: ${model.stats.variant_units} Variationsstellen`);
    show("syn");
  };

  /* ----------------------------------------------------------- synopsis */
  async function renderSynopsis() {
    const root = $("#view-syn");
    if (!model) {
      try { model = await api("GET", "/api/model"); } catch (e) {
        root.innerHTML = `<div class="export"><section class="panel"><h2>Noch keine Kollation</h2><p class="hint">Wählen Sie unter „Vorbereitung“ die Zeugen und starten Sie die Kollation.</p><button class="btn primary" data-goprep>Zur Vorbereitung</button></section></div>`;
        root.querySelector("[data-goprep]").addEventListener("click", () => show("prep"));
        return;
      }
    }
    if (syn) return;
    syn = PTASynopsis.create(root, model, { onSelect: openDrawer, base: model.settings.base });
    if (model.stale) toast("Die Einstellungen wurden seit dem letzten Lauf geändert. Kollation neu starten, um sie anzuwenden.");
  }

  async function edit(ops, keepKey) {
    // unit-level edits remember the tokens of their unit, so they survive later re-alignment edits
    for (const op of Array.isArray(ops) ? ops : [ops]) {
      if (op.unit && !op.anchors && syn) {
        const u = syn.data.units.find(x => x.key === op.unit);
        if (u) op.anchors = Object.values(u.cells).flatMap(c => c.tokens || []).slice(0, 60);
      }
    }
    try {
      model = await api("POST", "/api/edit", { ops: Array.isArray(ops) ? ops : [ops] });
      syn.update(model, keepKey);
      const failed = model.edit_status.filter(s => !s.ok).length;
      if (failed) toast(`${failed} Korrektur(en) konnten nicht angewendet werden – siehe Änderungsprotokoll.`, true);
    } catch (e) { toast(e.message, true); }
  }

  const SEG0_TIP = "Text vor dem ersten Abschnittsanker (milestone bzw. div), meist Titel oder Überschrift des Werkes.";
  let drawerSeq = 0;
  async function openDrawer(u0, api_) {
    const d = api_.drawer();
    const seq = ++drawerSeq;
    let u;
    try { u = await api("GET", "/api/unit?key=" + encodeURIComponent(u0.key)); } catch (e) { return toast(e.message, true); }
    if (seq !== drawerSeq) return;           // a newer selection is already loading
    Object.assign(api_.data.tokens, u.tokens);
    u.key = u0.key;
    const keep = [u.key, ...Object.values(u.cells).flatMap(c => c.tokens || [])];
    const rwits = c => (u.readings.find(r => r.c === c) || { wits: [] }).wits;
    d.classList.remove("hidden");
    const data = api_.data;
    const idx = data.units.findIndex(x => x.key === u.key);
    const lab = id => (data.witnesses.find(w => w.id === id) || {}).label || id;
    const prevU = data.units[idx - 1], nextU = data.units[idx + 1];
    const wits = data.witnesses.map(w => w.id).filter(id => id in u.cells);
    const lemR = u.readings.find(r => r.id === u.lem);

    const ED_KIND = { conjecture: t("Konjektur"), correction: t("Korrektur"), proposition: t("Vorschlag|proposition"), lacunam_indicavit: t("Lücke vermutet") };
    const srcName = ed => {
      if (ed.source || ed.resp) {
        const x = (st.project.sources || []).find(z => z.id === (ed.source || ed.resp));
        if (x) return x.name || x.id;
        if (ed.resp && ed.resp === (st.project.editor || {}).id) return st.project.editor.name || ed.resp;
        return ed.source || ed.resp;
      }
      return (st.project.editor || {}).name || "Bearbeiter/in";
    };
    // type and cause: recognised automatically unless set (or taken over) in the log
    const isAuto = (r, k) => !(r.override && k in r.override);
    // sub-variants (units.assign_parents): proposed automatically, confirmed like type and cause
    const plainR = u.readings.filter(r => !r.editorial);
    const hasSub = plainR.some(r => r.parent || r.parent_auto);
    const byId = Object.fromEntries(u.readings.map(r => [r.id, r]));
    const autoReadings = u.variant ? plainR.filter(r => isAuto(r, "type") || isAuto(r, "cause") || (hasSub && isAuto(r, "parent"))) : [];
    const subInfo = r => {
      if (!r.parent || !r.sub_diff) return "";
      const d = r.sub_diff, parts = [];
      if (d.missing) parts.push(t(d.missing === 1 ? "ohne 1 Wort" : "ohne {n} Wörter", { n: d.missing }));
      if (d.added) parts.push(t(d.added === 1 ? "1 Wort mehr" : "{n} Wörter mehr", { n: d.added }));
      if (d.changed) parts.push(t(d.changed === 1 ? "1 Stelle anders" : "{n} Stellen anders", { n: d.changed }));
      return `<span class="sub-diff${r.sub_warn ? " warn" : ""}"${r.sub_warn ? ` data-tip="${esc(t("Mehr als drei Wörter fehlen gegenüber der übergeordneten Lesart. Bitte prüfen, ob es wirklich eine Untervariante ist."))}"` : ""}>${r.sub_warn ? "⚠ " : ""}${esc(parts.join(", "))}</span>`;
    };
    const subSelect = r => !hasSub && !(u.variant && plainR.length >= 3) ? "" :
      `<label class="sub-of">${t("Untervariante von")} <select data-parent aria-label="${esc(t("Untervariante von"))}"${isAuto(r, "parent") ? ` class="auto" title="${esc(t("automatisch erkannt"))}"` : ""}>
        <option value="">${t("– eigene Lesart –")}</option>${plainR.filter(x => x !== r && x.c && !x.parent).map(x => `<option value="${esc(x.c)}" ${r.parent === x.id ? "selected" : ""}>${esc(x.t)}</option>`).join("")}</select></label>${subInfo(r)}`;
    // own readings first, each followed by its sub-variants
    const ordered = [];
    for (const r of u.readings) if (r.editorial || !r.parent) { ordered.push(r); for (const k of plainR) if (k.parent === r.id) ordered.push(k); }
    for (const r of u.readings) if (!ordered.includes(r)) ordered.push(r);
    const confirmBar = !u.variant || u.readings.filter(r => !r.editorial).length < 2 ? "" : autoReadings.length
      ? `<div class="confirm-bar"><span>${hasSub ? t("Typ, Ursache und Untervarianten automatisch erkannt") : t("Typ und Ursache automatisch erkannt")}</span><button class="btn small primary" data-confirm data-tip="Übernimmt die erkannten Typen und Ursachen aller Lesarten dieser Stelle als eigene Festlegung (eine Zeile im Änderungsprotokoll). Sie bleiben dann erhalten, auch wenn sich das Lemma ändert. Das Lemma selbst wird nicht gesetzt.">Erkennung übernehmen</button></div>`
      : `<div class="confirm-bar done"><span>${hasSub ? t("✓ Typ, Ursache und Untervarianten festgelegt") : t("✓ Typ und Ursache festgelegt")}</span></div>`;
    const readings = ordered.map(r => r.editorial ? `
      <div class="reading editorial${r.id === u.lem ? " is-lem" : ""}" data-ed="${esc(r.editorial.id)}">
        <div class="ed-kind">${ED_KIND[r.editorial.kind]}${r.editorial.cert ? ` (${t(r.editorial.cert === "low" ? "unsicher" : "wahrscheinlich")})` : ""}</div>
        <div class="rt">${r.t ? esc(r.t) : '<span class="empty-sign">Lücke vermutet</span>'}</div>
        <div class="meta"><span class="sig">${esc(srcName(r.editorial))}</span></div>
        <div class="meta">
          ${r.editorial.kind !== "lacunam_indicavit" ? `<label class="check" data-tip="Diese Lesart des Herausgebers als lem auszeichnen (im TEI lem mit @type und @resp bzw. @source)."><input type="radio" name="lem" ${r.id === u.lem ? "checked" : ""} data-edlem> Lemma</label>` : ""}
          <button class="btn small" data-ededit>Bearbeiten</button><button class="btn small" data-eddel>Entfernen</button>
        </div></div>` : `
      <div class="reading${r.id === u.lem ? " is-lem" : ""}${r.parent ? " is-sub" : ""}" data-c="${esc(r.c)}">
        <div class="rt">${r.c ? esc(r.t) : '<span class="empty-sign">om. (kein Text)</span>'}</div>
        <div class="meta"><span class="sig">${esc(r.wits.map(lab).join(" "))}</span>
          ${r.group ? `<span class="grp" title="orthographische Gruppe (rdgGrp)">Gruppe ${r.group}</span>` : ""}</div>
        <div class="meta">
          <label class="check" data-tip="Diese Lesart als lem auszeichnen. Für das volle PTA-Schema braucht jede Variationsstelle ein Lemma."><input type="radio" name="lem" ${r.id === u.lem ? "checked" : ""} data-lem> Lemma</label>
          <select data-type aria-label="Typ"${isAuto(r, "type") ? ' class="auto" title="automatisch erkannt"' : ""}>${TYPES.map(t => `<option value="${t}" ${(r.type || "") === t ? "selected" : ""}>${TYPE_LABEL[t]}</option>`).join("")}</select>
          <select data-cause aria-label="Ursache"${isAuto(r, "cause") ? ' class="auto" title="automatisch erkannt"' : ""}>${CAUSES.map(t => `<option value="${t}" ${(r.cause || "") === t ? "selected" : ""}>${CAUSE_LABEL[t]}</option>`).join("")}</select>
        </div>${subSelect(r) ? `<div class="meta">${subSelect(r)}</div>` : ""}</div>`).join("");

    // words of the unit (structure witness), for conjectures on a part of an invariant stretch
    const wordCid = (() => {
      const sw = st.project.structure_witness, ids = Object.keys(u.cells);
      return ids.find(i => i === sw + "_pc" || i === sw) || ids.find(i => !i.endsWith("_ac") && (u.cells[i].tokens || []).length) || ids[0];
    })();
    const words = wordCid ? (u.cells[wordCid].tokens || []) : [];
    const wtext = t => (data.tokens[t] || {}).t || "";
    const ranged = !u.variant && words.length > 1;
    const lemText = (lemR && !lemR.editorial ? lemR.t : (u.readings.filter(r => !r.editorial).sort((a, b) => b.wits.length - a.wits.length)[0] || {}).t) || "";
    const srcOptions = sel => `<option value="">eigene (${esc((st.project.editor || {}).name || "Bearbeiter/in")})</option>` +
      (st.project.sources || []).map(x => `<option value="${esc(x.id)}" ${sel === x.id ? "selected" : ""}>${esc(x.name || x.id)} (${x.kind === "bibl" ? "Edition" : "Person"})</option>`).join("") +
      `<option value="__new">Neue Person oder Edition …</option>`;
    const conjForm = `
      <h4>Konjektur oder Korrektur${tip("Lesart des Herausgebers an dieser Stelle. Im TEI: lem bzw. rdg mit @type conjecture (Konjektur), correction (kleine Korrektur, z. B. Orthographie), proposition (Vorschlag, mit @cert) oder lacunam_indicavit (vermutete Lücke, leer). Urheber: @resp verweist auf eine Person (eigene Konjekturen auf die/den Bearbeiter/in), @source auf eine frühere Edition; beide werden im teiHeader (listPerson, listBibl) angelegt.")}</h4>
      <div class="conj-form">
        <label for="cj-kind">Art</label><select id="cj-kind">
          <option value="conjecture">Konjektur</option><option value="correction">Korrektur</option>
          <option value="proposition">Vorschlag (proposuit)</option><option value="lacunam_indicavit">Lücke vermutet</option></select>
        ${u.inserted ? "" : `<label for="cj-place">Position${tip("An dieser Stelle: die Lesart steht statt des Wortlauts der Handschriften. Neue Zeile: für Text, den keine Handschrift hat (ergänzende Konjektur), oder eine vermutete Lücke zwischen zwei Wörtern; die Zeile wird vor bzw. nach dieser Stelle eingefügt, bei übereinstimmendem Text vor dem ersten bzw. nach dem letzten gewählten Wort.")}</label>
          <select id="cj-place"><option value="here">an dieser Stelle (statt des Wortlauts)</option><option value="before">neue Zeile davor</option><option value="after">neue Zeile danach</option></select>`}
        ${ranged ? `<label>Wörter</label><span><select id="cj-from" aria-label="von">${words.map((t, i) => `<option value="${i}">${esc(wtext(t))}</option>`).join("")}</select> bis
          <select id="cj-to" aria-label="bis">${words.map((t, i) => `<option value="${i}" ${i === 0 ? "selected" : ""}>${esc(wtext(t))}</option>`).join("")}</select></span>` : ""}
        <label for="cj-text" class="cj-t">Text</label><input type="text" id="cj-text" class="cj-t" lang="grc" value="${esc(ranged ? wtext(words[0]) : lemText)}">
        <label for="cj-src">Urheber</label><select id="cj-src">${srcOptions("")}</select>
        <span class="newsrc" hidden>
          <label for="ns-name">Name</label><input type="text" id="ns-name" placeholder="z. B. Paul Maas bzw. Oberg 1969">
          <label for="ns-id">Kürzel</label><input type="text" id="ns-id" placeholder="xml:id, z. B. Maas">
          <label for="ns-kind">Art</label><select id="ns-kind"><option value="person">Person (@resp)</option><option value="bibl">Edition (@source)</option></select>
          <label for="ns-ref">Normdaten</label><input type="text" id="ns-ref" placeholder="GND- oder Katalog-URL (optional)">
        </span>
        <label for="cj-cert" class="cj-c" hidden>Sicherheit</label><select id="cj-cert" class="cj-c" hidden><option value="">–</option><option value="low">niedrig</option><option value="high">hoch</option></select>
        <span></span><label class="check"><input type="checkbox" id="cj-lem" checked> als Lemma</label>
        <span></span><span class="actions"><button class="btn small primary" id="cj-add">Hinzufügen</button><button class="btn small" id="cj-cancel" hidden>Abbrechen</button></span>
      </div>`;

    // manuscripts without text here: omission ↔ lacuna
    const P_STATE = { omission: "Auslassung", lacuna: "Lücke", before: "setzt erst später ein (witStart)", after: "endet vorher (witEnd)" };
    const presence = (u.presence || []).length ? `
      <h4>Lücken und Zeugenbestand${tip("Zeugen ohne Text an dieser Stelle. Eine Auslassung ist eine Lesart (rdg type=omission). Eine Lücke bedeutet, dass der Zeuge hier nicht vorhanden ist (Blattverlust, Fragment): im TEI app type=witnesses mit lacunaStart/lacunaEnd, am Anfang oder Ende des Zeugen witStart/witEnd. Die Entscheidung gilt für den ganzen Abschnitt ohne Text dieses Zeugen. Automatisch gilt als Lücke, was länger ist als in der Vorbereitung eingestellt.")}</h4>
      <ul class="presence">${u.presence.map(o => `<li><span class="sg">${esc(o.label)}</span><span class="st">${t(P_STATE[o.state])} · ${t(o.words === 1 ? "{n} Wort" : "{n} Wörter", { n: o.words })}</span>
        <button class="btn small" data-pres="${esc(o.ms)}" data-val="${o.state === "omission" ? "1" : "0"}">${o.state === "omission" ? "als Lücke werten" : "als Auslassung werten"}</button></li>`).join("")}</ul>` : "";
    // alignment grid of the unit (rows × witnesses) with move / split controls
    if (!u.grid) u.grid = [{ id: "", cells: Object.fromEntries(Object.entries(u.cells).map(([w, c]) => [w, []])) }];
    let grid = `<div class="grid-wrap"><table class="grid"><thead><tr>${wits.map(w => `<th>${esc(lab(w))}</th>`).join("")}</tr></thead><tbody>`;
    u.grid.forEach((row, ri) => {
      if (ri > 0) {
        const at = firstToken(row, data);
        grid += `<tr class="split-line"><td colspan="${wits.length}"><button data-split="${esc(at)}" title="Stelle hier teilen">Stelle hier teilen</button></td></tr>`;
      }
      grid += "<tr>" + wits.map(w => {
        const cell = row.cells[w] || [];
        return "<td>" + cell.map((t, ti) => {
          const up = ti === 0 && (ri > 0 || (prevU && prevU.seg === u.seg));
          const down = ti === cell.length - 1 && (ri < u.grid.length - 1 || (nextU && nextU.seg === u.seg));
          const first = ti === 0, last = ti === cell.length - 1;
          return `<span class="chip">${esc((data.tokens[t] || {}).t)}${up ? `<button data-move="${esc(t)}" data-dir="prev" title="in die Zeile darüber" aria-label="nach oben">↑</button>` : ""}${down ? `<button data-move="${esc(t)}" data-dir="next" title="in die Zeile darunter" aria-label="nach unten">↓</button>` : ""}` +
            `${first ? `<button data-move="${esc(t)}" data-dir="newprev" data-row="${ri}" title="in eine neue Zeile darüber (mit gleichlautenden Wörtern der anderen Zeugen dieser Zeile)" aria-label="in neue Zeile darüber">⤒</button>` : ""}` +
            `${last ? `<button data-move="${esc(t)}" data-dir="newnext" data-row="${ri}" title="in eine neue Zeile darunter (mit gleichlautenden Wörtern der anderen Zeugen dieser Zeile)" aria-label="in neue Zeile darunter">⤓</button>` : ""}</span>`;
        }).join("") + "</td>";
      }).join("") + "</tr>";
    });
    grid += "</tbody></table></div>";

    // folios with the sigla of the manuscripts: "381v (La) · 112r (Pg) · 113r (Ps Vi)"
    const pages = (() => {
      const byPage = new Map();
      for (const ms of [...new Set(data.witnesses.map(w => w.ms))]) {
        const ws = data.witnesses.filter(w => w.ms === ms);
        const w = ws.find(x => x.id in u.cells && x.layer !== "ac") || ws.find(x => x.id in u.cells);
        const pg = w && (u.cells[w.id].pages || []);
        if (!pg || !pg.length) continue;
        const k = pg.length > 1 ? pg[0] + "–" + pg[pg.length - 1] : pg[0];
        if (!byPage.has(k)) byPage.set(k, []);
        byPage.get(k).push(w.siglum || ms);
      }
      return [...byPage].map(([k, sig]) => `${k} (${sig.join(" ")})`);
    })();
    d.innerHTML = `
      <div class="row" style="justify-content:space-between;margin-top:0">
        <h3>Stelle ${idx + 1}${u.inserted ? " · eingefügte Zeile" : u.variant ? "" : " (ohne Varianz)"}</h3>
        <span><button class="btn small" data-nav="-1" title="vorige Variationsstelle (k)">◀</button>
        <button class="btn small" data-nav="1" title="nächste Variationsstelle (j)">▶</button>
        <button class="icon-btn" data-close>Schließen</button></span></div>
      <div class="sub">${u.seg === "0" ? `<span data-tip="${esc(SEG0_TIP)}">Titel / Vorspann</span>` : "Abschnitt " + esc(u.seg)}${pages.length ? " · " + pages.map(esc).join(" · ") : ""}${u.transposition ? " · Umstellung" : ""}</div>
      ${confirmBar}
      ${u.variant ? `<h4>Lesarten${tip("Eine Lesart je unterschiedlichem Wortlaut. „Gruppe“: orthographisch zusammengehörige Lesarten, im TEI in einem rdgGrp. Typ und Ursache sind aus der Analyse vorbelegt und werden als @type und @cause exportiert. Gestrichelt umrandet: automatisch erkannt; ändert sich das Lemma, wird neu erkannt. Selbst gewählte oder mit „Erkennung übernehmen“ bestätigte Werte bleiben fest.")}</h4>${readings}
        <div class="actions">${lemR ? `<button class="btn small" data-unlem>Lemma entfernen</button>` : ""}
        ${hasSub ? "" : `<label class="check" data-tip="${(u.nrows || 1) > 1 && lemR ? "Kleinvarianten innerhalb der Zeugen des Lemmas werden als inneres app im lem ausgezeichnet, wie im PTA-Schema vorgesehen." : "Erst ein Lemma wählen; möglich nur bei Stellen, die aus mehreren Zeilen zusammengesetzt sind."}"><input type="checkbox" data-nest ${u.nest ? "checked" : ""} ${(u.nrows || 1) > 1 && lemR ? "" : "disabled"}> Varianten im Lemma verschachteln</label>`}</div>` : ""}
      ${conjForm}
      ${presence}
      ${u.variant && !u.inserted ? `<h4>Alignment dieser Stelle${tip("Die Zeilen des Aligners in dieser Stelle, eine Spalte je Zeuge bzw. Korrekturschicht. ↑ und ↓ verschieben ein Wort in die Nachbarzeile, auch über die Grenze der Stelle hinweg. „Stelle hier teilen“ macht aus einer Stelle zwei.")}</h4>${grid}` : (u.inserted ? `<p class="muted">Neue Zeile ohne Text in den Handschriften, für eine Lesart des Herausgebers.</p>`
        : `<p class="muted">Alle Zeugen stimmen hier überein (${words.length || Object.values(u.cells)[0].n_tok || ""} Wörter).</p>`)}
      ${u.inserted ? `<div class="actions"><button class="btn small" data-delrow data-tip="Entfernt die Zeile und alle Einträge zu ihr aus dem Änderungsprotokoll.">Zeile entfernen</button></div>` : ""}
      <div class="actions" style="margin-top:8px"${u.inserted ? " hidden" : ""}>
        <button class="btn small" data-tip="Diese und die vorige Stelle werden eine Variationsstelle (ein app)." data-join="prev" ${prevU && prevU.seg === u.seg ? "" : "disabled"}>Mit vorheriger Stelle zusammenfassen</button>
        <button class="btn small" data-tip="Diese und die nächste Stelle werden eine Variationsstelle (ein app)." data-join="next" ${nextU && nextU.seg === u.seg ? "" : "disabled"}>Mit nächster zusammenfassen</button>
      </div>
      ${u.inserted ? "" : `      <h4>Weite Umstellung${tip("Eine Wortfolge fehlt an einer Stelle und steht an einer anderen. Im TEI werden beide Stellen als app ausgezeichnet und mit @prev/@next verbunden (Auslassung und Hinzufügung). Vorschläge der automatischen Erkennung werden erst nach „Übernehmen“ exportiert.")}</h4>
      ${u.suggest ? (() => {
        const otherKey = u.suggest.next || u.suggest.prev;
        const k = data.units.findIndex(x => x.key === otherKey);
        return `<div class="suggest-box"><p>Vorschlag: ${u.suggest.next ? "Diese Stelle und Stelle" : "Stelle"} <a href="#" data-goto="${esc(otherKey)}">${k + 1}</a> ${u.suggest.next ? "bilden" : "und diese Stelle bilden"} eine weite Umstellung (Auslassung an der einen, Hinzufügung an der anderen Stelle).</p>
          <div class="actions"><button class="btn small primary" data-accept>Übernehmen</button><button class="btn small" data-reject>Verwerfen</button></div></div>`;
      })() : ""}
      ${u.link ? `<p>Verknüpft mit Stelle ${data.units.findIndex(x => x.key === (u.link.next || u.link.prev)) + 1} (${u.link.next ? "Ziel" : "Herkunft"}). <button class="btn small" data-unlink>Verknüpfung lösen</button></p>`
        : `<div class="row"><label>Mit Stelle Nr.<input type="number" min="1" max="${data.units.length}" data-linkto style="width:6em"></label><button class="btn small" data-link>verknüpfen</button></div>
           <p class="muted" style="font-size:13px">Auslassung hier und Hinzufügung dort werden im TEI über <code>@prev</code>/<code>@next</code> verbunden.</p>`}
`}
      <h4>Notiz zur Stelle${tip("Erscheint im TEI als note innerhalb des app.")}</h4>
      <textarea data-note placeholder="erscheint als note im app">${esc(u.note || "")}</textarea>
      <h4>Änderungsprotokoll${tip("Alle Korrekturen werden in der Projektdatei gespeichert und nach jedem neuen Kollationslauf wieder angewendet. Rot markiert: Korrektur passt nicht mehr zum neuen Alignment und wurde übergangen.")}</h4>
      <div class="actions" style="margin-bottom:6px"><button class="btn small" data-undo ${model.edits.length ? "" : "disabled"}>Letzte Korrektur rückgängig</button></div>
      <div class="log">${model.edits.length ? model.edits.map((e, i) => {
        const s = model.edit_status.find(x => x.edit === i);
        return `<div class="${s && !s.ok ? "bad" : ""}"><span style="flex:1"><span class="lnum">${i + 1}.</span> ${esc(describe(e, data))}${s && !s.ok ? " – " + t("nicht angewendet") : ""}</span><button class="icon-btn" data-rm="${i}">Entfernen</button></div>`;
      }).reverse().join("") : '<div class="muted">Noch keine Korrekturen.</div>'}</div>`;

    d.querySelector("[data-close]").onclick = () => { d.classList.add("hidden"); };
    for (const b of $$("[data-nav]", d)) b.onclick = () => api_.navigate(+b.dataset.nav);
    const cb = $("[data-confirm]", d);
    if (cb) cb.onclick = () => edit({ op: "confirm", unit: u.key,
      readings: autoReadings.map(r => {
        const o = { reading: r.c, wits: r.wits };
        if (isAuto(r, "type")) o.type = r.type || null;
        if (isAuto(r, "cause")) o.cause = r.cause || null;
        if (hasSub && isAuto(r, "parent")) o.parent = r.parent ? byId[r.parent].c : null;
        return o;
      }) }, u.key);
    for (const rd of $$(".reading:not(.editorial)", d)) {
      const c = rd.dataset.c;
      $("[data-lem]", rd).onchange = () => edit({ op: "lem", unit: u.key, reading: c, wits: rwits(c) }, u.key);
      $("[data-type]", rd).onchange = e => edit({ op: "attr", unit: u.key, reading: c, wits: rwits(c), key: "type", value: e.target.value || null }, u.key);
      $("[data-cause]", rd).onchange = e => edit({ op: "attr", unit: u.key, reading: c, wits: rwits(c), key: "cause", value: e.target.value || null }, u.key);
      const ps = $("[data-parent]", rd);
      if (ps) ps.onchange = e => edit({ op: "attr", unit: u.key, reading: c, wits: rwits(c), key: "parent", value: e.target.value || null }, u.key);
    }
    for (const rd of $$(".reading.editorial", d)) {
      const id = rd.dataset.ed, r = u.readings.find(x => x.editorial && x.editorial.id === id);
      const el = $("[data-edlem]", rd); if (el) el.onchange = () => edit({ op: "lem", unit: u.key, editorial: id }, u.key);
      $("[data-eddel]", rd).onclick = () => edit({ op: "conj", unit: u.key, id, delete: true }, u.key);
      $("[data-ededit]", rd).onclick = () => {
        $("#cj-kind", d).value = r.editorial.kind; $("#cj-text", d).value = r.t || "";
        $("#cj-src", d).value = r.editorial.source || r.editorial.resp && r.editorial.resp !== (st.project.editor || {}).id && r.editorial.resp || "";
        $("#cj-cert", d).value = r.editorial.cert || ""; $("#cj-lem", d).checked = r.id === u.lem;
        $("#cj-add", d).textContent = "Speichern"; $("#cj-add", d).dataset.id = id; $("#cj-cancel", d).hidden = false;
        for (const x of $$("#cj-from, #cj-to", d)) x.disabled = true;
        if ($("#cj-place", d)) { $("#cj-place", d).value = "here"; $("#cj-place", d).disabled = true; }
        syncConj(); $("#cj-text", d).focus();
      };
    }
    let placeTouched = false;
    const prefill = $("#cj-text", d).value;
    const syncConj = () => {
      const kind = $("#cj-kind", d).value;
      const pl = $("#cj-place", d);
      if (pl && !placeTouched) pl.value = kind === "lacunam_indicavit" ? "after" : "here";
      if (pl && pl.value !== "here" && $("#cj-text", d).value === prefill) $("#cj-text", d).value = "";
      if (pl && pl.value === "here" && !$("#cj-text", d).value) $("#cj-text", d).value = prefill;
      for (const x of $$(".cj-t", d)) x.hidden = kind === "lacunam_indicavit";
      for (const x of $$(".cj-c", d)) x.hidden = kind !== "proposition";
      $("#cj-lem", d).disabled = kind === "lacunam_indicavit";
      if (kind === "lacunam_indicavit") $("#cj-lem", d).checked = false;
      $(".newsrc", d).hidden = $("#cj-src", d).value !== "__new";
    };
    $("#cj-kind", d).onchange = syncConj; $("#cj-src", d).onchange = syncConj;
    if ($("#cj-place", d)) $("#cj-place", d).onchange = () => { placeTouched = true; syncConj(); };
    const rangeText = () => {
      const a = +$("#cj-from", d).value, b = Math.max(a, +$("#cj-to", d).value);
      $("#cj-to", d).value = b;
      $("#cj-text", d).value = words.slice(a, b + 1).map(wtext).join(" ");
    };
    if ($("#cj-from", d)) { $("#cj-from", d).onchange = rangeText; $("#cj-to", d).onchange = rangeText; }
    $("#cj-cancel", d).onclick = () => openDrawer(u0, api_);
    $("#cj-add", d).onclick = async () => {
      const kind = $("#cj-kind", d).value, text = $("#cj-text", d).value.trim();
      if (kind !== "lacunam_indicavit" && !text) return toast("Bitte den Text der Konjektur bzw. Korrektur eingeben.", true);
      let src = $("#cj-src", d).value;
      if (src === "__new") {
        const id = $("#ns-id", d).value.trim().replace(/\s+/g, "_"), name = $("#ns-name", d).value.trim();
        if (!/^[A-Za-z_][\w.-]*$/.test(id)) return toast("Kürzel: Buchstaben, Ziffern, _ - . (für xml:id), beginnend mit einem Buchstaben.", true);
        if ((st.project.sources || []).some(x => x.id === id) || data.witnesses.some(w => w.ms === id))
          return toast("Dieses Kürzel ist schon vergeben.", true);
        st.project.sources = [...(st.project.sources || []), { id, name: name || id, kind: $("#ns-kind", d).value, ref: $("#ns-ref", d).value.trim() || undefined }];
        await api("PUT", "/api/project", { sources: st.project.sources });
        src = id;
      }
      const sx = (st.project.sources || []).find(x => x.id === src);
      const id = $("#cj-add", d).dataset.id || "c" + Date.now().toString(36);
      const op = { op: "conj", id, kind, text: kind === "lacunam_indicavit" ? "" : text, cert: kind === "proposition" ? ($("#cj-cert", d).value || null) : null };
      if (sx && sx.kind === "bibl") op.source = src; else if (src) op.resp = src;
      const asLem = $("#cj-lem", d).checked && kind !== "lacunam_indicavit";
      const ops = [];
      const place = $("#cj-place", d) && !$("#cj-add", d).dataset.id ? $("#cj-place", d).value : "here";
      if (place !== "here") {
        // a new row before or after this place (ranged: before the first / after the last chosen word)
        const iid = "i" + Date.now().toString(36);
        let ref = u.key, anchors = keep.slice(0, 60);
        if (ranged) {
          const a = +$("#cj-from", d).value, b = Math.max(a, +$("#cj-to", d).value);
          if (place === "before") { if (a > 0) ops.push({ op: "split", at: words[a] }); ref = words[a]; anchors = [words[a]]; }
          else { if (b < words.length - 1) ops.push({ op: "split", at: words[b + 1] }); ref = words[b]; anchors = [words[b]]; }
        }
        ops.push({ op: "insert", id: iid, [place]: ref, anchors });
        ops.push(Object.assign(op, { unit: "ins:" + iid, anchors: [] }));
        if (asLem) ops.push({ op: "lem", unit: "ins:" + iid, anchors: [], editorial: id });
        await edit(ops, "ins:" + iid);
        return;
      }
      if (ranged && !$("#cj-add", d).dataset.id) {
        const a = +$("#cj-from", d).value, b = +$("#cj-to", d).value;
        if (a > 0) ops.push({ op: "split", at: words[a] });
        if (b < words.length - 1) ops.push({ op: "split", at: words[b + 1] });
        Object.assign(op, { unit: words[a], anchors: words.slice(a, b + 1) });
        ops.push(op);
        if (asLem) ops.push({ op: "lem", unit: words[a], anchors: words.slice(a, b + 1), editorial: id });
        await edit(ops, words[a]);
        return;
      }
      op.unit = u.key;
      ops.push(op);
      if (asLem) ops.push({ op: "lem", unit: u.key, editorial: id });
      else if (u.lem === "e:" + id) ops.push({ op: "lem", unit: u.key, reading: null });
      await edit(ops, u.key);
    };
    syncConj();
    const delrow = $("[data-delrow]", d);
    if (delrow) delrow.onclick = async () => {
      const iid = u.key.slice(4);
      const idx = model.edits.map((e, i) => ((e.op === "insert" && String(e.id) === iid) || e.unit === u.key) ? i : -1).filter(i => i >= 0);
      model = await api("POST", "/api/edits/remove", { indices: idx });
      syn.update(model, prevU ? prevU.key : null);
    };
    for (const b of $$("[data-pres]", d)) b.onclick = () => edit({ op: "lacuna", ms: b.dataset.pres, at: u.key, value: b.dataset.val === "1" }, keep);
    const unlem = $("[data-unlem]", d); if (unlem) unlem.onclick = () => edit({ op: "lem", unit: u.key, reading: null }, u.key);
    const nest = $("[data-nest]", d); if (nest) nest.onchange = () => edit({ op: "nest", unit: u.key, value: nest.checked }, u.key);
    for (const b of $$("[data-move]", d)) b.onclick = () => {
      const op = { op: "move", token: b.dataset.move, dir: b.dataset.dir };
      if (op.dir === "newprev" || op.dir === "newnext") {
        // the same word of the other witnesses in this row (e.g. the other correction layer) goes along
        const row = u.grid[+b.dataset.row], txt = s => ((data.tokens[s] || {}).t || "").toLowerCase();
        op.with = Object.values(row.cells).map(c => c.length ? c[op.dir === "newprev" ? 0 : c.length - 1] : null)
          .filter(x => x && x !== op.token && txt(x) === txt(op.token));
      }
      edit(op, keep);
    };
    for (const b of $$("[data-split]", d)) b.onclick = () => edit({ op: "split", at: b.dataset.split }, keep);
    for (const b of $$("[data-join]", d)) b.onclick = () => {
      if (b.dataset.join === "prev") edit({ op: "join", at: u.key }, prevU.key);
      else edit({ op: "join", at: nextU.key }, keep);
    };
    const link = $("[data-link]", d); if (link) link.onclick = () => {
      const n = +$("[data-linkto]", d).value; const other = data.units[n - 1];
      if (!other || other === u) return toast("Bitte eine andere, gültige Stellennummer angeben.", true);
      const [a, b] = data.units.indexOf(other) > idx ? [u, other] : [other, u];
      edit({ op: "link", a: a.key, b: b.key }, u.key);
    };
    const unlink = $("[data-unlink]", d); if (unlink) unlink.onclick = () => edit({ op: "unlink", a: u.key }, u.key);
    const accept = $("[data-accept]", d);
    if (accept) accept.onclick = () => {
      const other = u.suggest.next || u.suggest.prev;
      const [a, b] = u.suggest.next ? [u.key, other] : [other, u.key];
      edit({ op: "link", a, b }, u.key);
    };
    const reject = $("[data-reject]", d); if (reject) reject.onclick = () => edit({ op: "reject_link", a: u.key }, u.key);
    for (const g of $$("[data-goto]", d)) g.onclick = ev => { ev.preventDefault(); api_.select(g.dataset.goto, false); };
    $("[data-note]", d).onchange = e => edit({ op: "attr", unit: u.key, reading: null, key: "note", value: e.target.value }, u.key);
    $("[data-undo]", d).onclick = async () => { model = await api("POST", "/api/undo"); syn.update(model, keep); };
    for (const b of $$("[data-rm]", d)) b.onclick = async () => { model = await api("POST", "/api/edits/remove", { indices: [+b.dataset.rm] }); syn.update(model, keep); };
  }

  function firstToken(row, data) {
    for (const w of data.witnesses) if (row.cells[w.id] && row.cells[w.id].length) return row.cells[w.id][0];
    return null;
  }
  function describe(e, data) {
    const tok = id => String(id || "").startsWith("ins:") ? t("neue Zeile") : (data.tokens[id] || {}).t || id;
    const KIND = { conjecture: "Konjektur", correction: "Korrektur", proposition: "Vorschlag|proposition", lacunam_indicavit: "vermutete Lücke" };
    switch (e.op) {
      case "move": return t({ prev: "„{w}“ nach oben verschoben", next: "„{w}“ nach unten verschoben",
        newprev: "„{w}“ in eine neue Zeile darüber verschoben", newnext: "„{w}“ in eine neue Zeile darunter verschoben" }[e.dir] || "„{w}“ verschoben", { w: tok(e.token) });
      case "split": return t("Stelle vor „{w}“ geteilt", { w: tok(e.at) });
      case "join": return t("Stelle ab „{w}“ mit vorheriger zusammengefasst", { w: tok(e.at) });
      case "lem": return e.editorial ? t("Lesart des Herausgebers bei „{w}“ als Lemma gewählt", { w: tok(e.unit) })
        : e.reading == null ? t("Lemma bei „{w}“ entfernt", { w: tok(e.unit) }) : t("Lemma „{w}“ gewählt", { w: e.reading || "om." });
      case "attr": return e.key === "note" ? t("Notiz bei „{w}“", { w: tok(e.unit) })
        : e.key === "parent" ? (e.value ? t("„{w}“ als Untervariante von „{v}“", { w: e.reading || "om.", v: e.value }) : t("„{w}“ als eigene Lesart", { w: e.reading || "om." }))
        : t(e.key === "type" ? "Typ von „{w}“: {v}" : "Ursache von „{w}“: {v}", { w: e.reading || "om.", v: e.value || "–" });
      case "confirm": return t("Erkennung bei „{w}“ übernommen", { w: tok(e.unit) });
      case "nest": return t(e.value ? "Verschachtelung bei „{w}“ an" : "Verschachtelung bei „{w}“ aus", { w: tok(e.unit) });
      case "link": return t("Umstellung „{a}“ ↔ „{b}“ verknüpft", { a: tok(e.a), b: tok(e.b) });
      case "unlink": return t("Verknüpfung bei „{w}“ gelöst", { w: tok(e.a) });
      case "reject_link": return t("Vorschlag weite Umstellung bei „{w}“ verworfen", { w: tok(e.a) });
      case "insert": return e.delete ? t("Eingefügte Zeile entfernt") : e.before ? t("Neue Zeile vor „{w}“ eingefügt", { w: tok(e.before) }) : t("Neue Zeile nach „{w}“ eingefügt", { w: tok(e.after) });
      case "lacuna": return t(e.value ? "{ms} bei „{w}“ als Lücke gewertet" : "{ms} bei „{w}“ als Auslassung gewertet", { ms: e.ms, w: tok(e.at) });
      case "conj": return e.delete ? t("Lesart des Herausgebers bei „{w}“ entfernt", { w: tok(e.unit) })
        : t("{kind}{text} bei „{w}“", { kind: t(KIND[e.kind] || "Konjektur"), text: e.text ? " „" + e.text + "“" : "", w: tok(e.unit) });
      default: return e.op;
    }
  }

  /* ------------------------------------------------------------- export */
  async function renderExport() {
    api("GET", "/api/schema").then(showSchema).catch(() => {});
    try { model = model || await api("GET", "/api/model"); }
    catch (e) { $("#exp-stats").textContent = "Noch keine Kollation – bitte zuerst unter „Vorbereitung“ starten."; return; }
    const s = model.stats;
    const parts = [t("{a} Variationsstellen in {b} Abschnitten", { a: s.variant_units, b: model.segments.length }),
      t("{n} mit Lemma", { n: s.with_lem }), t("{n} rein orthographisch", { n: s.orthographic_only })];
    if (s.editorial) parts.push(t("{n} Lesarten des Herausgebers", { n: s.editorial }));
    if (s.lacunae) parts.push(t("{n} Lücken in Zeugen", { n: s.lacunae }));
    $("#exp-stats").textContent = parts.join(", ") + "; " + t("{n} manuelle Korrekturen.", { n: model.edits.length }) +
      (s.with_lem === s.variant_units ? " " + t("Alle Stellen haben ein Lemma: die Datei sollte auch gegen das volle PTA-Schema gültig sein.") : "");
  }
  for (const b of $$("[data-save]")) b.onclick = async () => {
    if (!st.path) return toast("Bitte zuerst das Projekt speichern; Exporte landen neben der Projektdatei.", true);
    const res = await busy("Export …", () => api("POST", `/api/export/${b.dataset.save}/save`, { lang: PTAI18N.lang }));
    toast(res.note ? res.note : "Gespeichert: " + res.saved, !!res.note);
  };
  // which PTA schema is used: the copy shipped or a newer one from GitHub (pta_collate/schema_store.py)
  const fmtTime = s => s ? new Date(s * 1000).toLocaleString(PTAI18N.lang === "en" ? "en-GB" : "de-DE", { dateStyle: "medium", timeStyle: "short" }) : "";
  function showSchema(s) {
    const el = $("#schema-info");
    if (!el || !s) return;
    const what = s.source === "github"
      ? t("PTA-Schema: neue Fassung aus GitHub, übernommen am {d}.", { d: fmtTime(s.updated) })
      : t("PTA-Schema: mitgelieferte Fassung.");
    const when = !s.enabled ? t("Automatische Prüfung ausgeschaltet.")
      : s.error ? t("Prüfung nicht möglich ({e}); es gilt die bisherige Fassung.", { e: s.error })
      : s.checked ? t("Zuletzt mit GitHub verglichen: {d}.", { d: fmtTime(s.checked) }) : t("Noch nicht mit GitHub verglichen.");
    el.className = "schema-info" + (s.error ? " warn" : "");
    el.innerHTML = `${esc(what)} ${esc(when)} <button class="link-btn" id="schema-check">${esc(t("Jetzt prüfen"))}</button>`;
    $("#schema-check").onclick = async () => {
      const r = await busy(t("Schema wird mit GitHub verglichen …"), () => api("POST", "/api/schema/check"));
      showSchema(r);
      toast(r.error ? t("Prüfung nicht möglich: {e}", { e: r.error }) : r.updated && Date.now() / 1000 - r.updated < 60
        ? t("Neue Fassung des PTA-Schemas übernommen.") : t("Das PTA-Schema ist aktuell."), !!r.error);
    };
  }
  $("#validate").onclick = async () => {
    const res = await busy("TEI wird geprüft …", () => api("POST", "/api/validate", { full: true }));
    showSchema(res.schema);
    const part = (r, name) => {
      const errs = [...r.relaxng.errors, ...r.schematron.errors];
      return `<p><span class="${r.valid ? "valid-ok" : "valid-bad"}">${r.valid ? "gültig" : "nicht gültig"}</span> gegen ${name}` +
        (r.schematron.warnings ? ` <span class="muted">(${r.schematron.warnings} Hinweise: Stellen ohne Lemma)</span>` : "") + "</p>" +
        (errs.length ? `<pre class="errors">${esc(errs.slice(0, 12).join("\n"))}</pre>` : "");
    };
    $("#valid-out").innerHTML = part(res.collation, "tei-pta_collation") + part(res.full, "das volle PTA-Schema");
  };

  /* ------------------------------------------------------------ variance */
  // The variance overview (static/varianz) reads the TEI export of the current collation.
  let varStamp = null;
  function varianceUrl() {
    const th = PTATheme.get();
    return "/static/varianz/index.html?lang=" + encodeURIComponent(document.documentElement.lang || "de") +
      (th !== "auto" ? "&theme=" + th : "") +
      "&xml=" + encodeURIComponent("/api/export/tei?keys=1&t=" + Date.now());
  }
  async function renderVariance(force) {
    if (!st.has_result) {
      $("#var-info").textContent = "Noch keine Kollation – bitte zuerst unter „Vorbereitung“ starten.";
      $("#var-frame").removeAttribute("src");
      return;
    }
    try { model = model || await api("GET", "/api/model"); } catch (e) { return toast(e.message, true); }
    const stamp = JSON.stringify([st.result_info && st.result_info.created, model.edits.length, JSON.stringify(model.edits.slice(-1))]);
    $("#var-info").textContent = `${model.stats.variant_units} Variationsstellen, ${model.stats.with_lem} mit Lemma`;
    if (!force && stamp === varStamp && $("#var-frame").getAttribute("src")) return;
    varStamp = stamp;
    const url = varianceUrl();
    $("#var-frame").src = url;
    $("#var-window").href = url;
  }
  $("#var-reload").onclick = () => renderVariance(true);
  // "show in graph" in the variance overview: open the unit in the synopsis with the variant graph
  window.addEventListener("message", async e => {
    const f = $("#var-frame");
    if (e.origin !== location.origin || !f || e.source !== f.contentWindow) return;
    const d = e.data || {};
    if (d.type !== "pta-show-unit" || typeof d.key !== "string") return;
    show("syn");
    await renderSynopsis();
    if (!syn || !model || !model.units.some(u => u.key === d.key)) return toast(t("Diese Stelle ist in der Synopse nicht zu finden."), true);
    const g = document.querySelector('#view-syn [data-v="graph"]');
    if (g && !g.checked) { g.checked = true; g.dispatchEvent(new Event("input")); }
    syn.select(d.key);
  });
  $("#open-var").onclick = () => show("var");

  /* -------------------------------------------------------- colour scheme */
  const themeButtons = () => {
    for (const b of $$("[data-theme-set]")) b.setAttribute("aria-pressed", String(b.dataset.themeSet === PTATheme.get()));
  };
  for (const b of $$("[data-theme-set]")) b.onclick = () => {
    PTATheme.set(b.dataset.themeSet);
    themeButtons();
    if ($("#var-window").getAttribute("href")) $("#var-window").href = varianceUrl();   // own window: same scheme
  };
  themeButtons();

  /* ------------------------------------------------------------ language */
  for (const a of $$('a[href^="/api/export/"]')) a.href = a.getAttribute("href") + "?lang=" + PTAI18N.lang;
  for (const b of $$(".lang-switch [data-lang]")) {
    b.setAttribute("aria-pressed", String(b.dataset.lang === PTAI18N.lang));
    b.onclick = () => { if (b.dataset.lang !== PTAI18N.lang) PTAI18N.setLang(b.dataset.lang); };
  }

  /* --------------------------------------------------------------- init */
  PTASynopsis.installTips(document);
  (async function init() {
    st = await api("GET", "/api/state");
    $("#about-version").textContent = st.version || "–";
    for (const el of $$("[data-version]")) el.textContent = st.version || "";
    renderStatus();
    const view = (location.hash || "").slice(1);
    show(["prep", "syn", "exp", "var", "about"].includes(view) ? view : (st.has_result ? "syn" : "prep"));
  })().catch(e => toast(e.message, true));
})();
