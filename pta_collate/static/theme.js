/* Colour scheme: "auto" (as set in the operating system), "light" or "dark".

   Loaded in <head>, so the page is drawn in the right scheme from the start. The choice is
   kept in the browser and – for browsers that do not allow site storage – in the address
   (?theme=light|dark). The stylesheets react to <html data-theme="…">; without the attribute
   they follow prefers-color-scheme. The variance overview (iframe) gets the same attribute. */
(function () {
  "use strict";
  const KEY = "pta-ui-theme";
  const ok = t => t === "auto" || t === "light" || t === "dark";
  let theme = null;
  try { theme = new URLSearchParams(location.search).get("theme"); } catch (e) { /* no URL parameters */ }
  if (!ok(theme)) { try { theme = localStorage.getItem(KEY); } catch (e) { theme = null; } }
  if (!ok(theme)) theme = "auto";

  function apply(doc, t) {
    if (t === "auto") doc.documentElement.removeAttribute("data-theme");
    else doc.documentElement.setAttribute("data-theme", t);
  }
  apply(document, theme);

  function set(t) {
    if (!ok(t)) return;
    theme = t;
    apply(document, t);
    try { localStorage.setItem(KEY, t); } catch (e) { /* storage blocked: the address keeps it */ }
    try {
      const u = new URL(location.href);
      if (t === "auto") u.searchParams.delete("theme"); else u.searchParams.set("theme", t);
      history.replaceState(history.state, "", u.toString());
    } catch (e) { /* ignore */ }
    for (const f of document.querySelectorAll("iframe")) {
      try { if (f.contentDocument) apply(f.contentDocument, t); } catch (e) { /* other origin */ }
    }
    document.dispatchEvent(new CustomEvent("pta-theme", { detail: t }));
  }

  window.PTATheme = { get: () => theme, set };
})();
