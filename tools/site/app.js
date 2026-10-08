const $ = id => document.getElementById(id);
const el = (tag, props = {}, ...children) => {
  const n = Object.assign(document.createElement(tag), props);
  n.append(...children);
  return n;
};
// Text with the search term wrapped in <mark>, built from text nodes only.
const marked = (text, term) => {
  const out = document.createDocumentFragment();
  const low = text.toLowerCase();
  let i = 0, at;
  while (term && (at = low.indexOf(term, i)) !== -1) {
    out.append(text.slice(i, at), el("mark", { textContent: text.slice(at, at + term.length) }));
    i = at + term.length;
  }
  out.append(text.slice(i));
  return out;
};

fetch("index.json").then(r => r.json()).then(d => {
  document.title = d.title;
  $("title").textContent = d.title;
  $("description").textContent = d.description;
  const addUrl = d.repo ? `https://github.com/${d.repo}/issues/new?template=submission.yml` : "";
  if (addUrl) { $("add").href = addUrl; $("add").hidden = false; }

  const paint = term => {
    const toc = $("toc"), main = $("sections");
    toc.replaceChildren(); main.replaceChildren();
    let shown = 0;
    for (const s of d.sections) {
      const all = d.entries.filter(e => e.section === s.id);
      const items = all
        .filter(e => `${e.name} ${e.description} ${e.owner}`.toLowerCase().includes(term))
        .sort((a, b) => a.name.localeCompare(b.name));
      shown += items.length;
      toc.append(el("a", { href: "#" + s.id, className: items.length ? "" : "empty" },
        el("span", { textContent: s.name }), el("span", { className: "count", textContent: items.length })));
      if (term && !items.length) continue;

      const sec = el("section", { id: s.id }, el("h2", { textContent: s.name }));
      if (s.description) sec.append(el("p", { className: "about", textContent: s.description }));
      if (!all.length) {
        const p = el("p", { className: "none", textContent: "Nothing here yet. " });
        if (addUrl) p.append(el("a", { href: addUrl, textContent: "Add the first one" }), ".");
        sec.append(p);
      }
      const ol = el("ol");
      for (const e of items) {
        // Only https URLs are linked: the content comes from third-party issues.
        const a = el("a", { rel: "noopener" }, marked(e.name, term));
        if (/^https:\/\//.test(e.url)) a.href = e.url;
        const row = el("div", { className: "row" }, a, el("span", { className: "leader" }));
        if (e.owner) row.append(el("span", { className: "owner" }, marked(e.owner, term)));
        ol.append(el("li", {}, row, el("p", {}, marked(e.description, term))));
      }
      sec.append(ol); main.append(sec);
    }
    if (term && !shown) main.append(el("p", { className: "none", textContent: `No repositories match “${term}”.` }));
  };
  paint("");
  $("search").addEventListener("input", ev => paint(ev.target.value.trim().toLowerCase()));
});
