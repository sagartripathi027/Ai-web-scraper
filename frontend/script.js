/* ─────────────────────────────────────────────
   AI Web Scraper — script.js
   Frontend logic: calls FastAPI backend at /scrape
───────────────────────────────────────────── */

const API_BASE = "http://127.0.0.1:8000";

let allLinks = [];

/* ── Main scrape function ── */
async function scrape() {
  const raw = document.getElementById("urlInput").value.trim();
  if (!raw) {
    showError("Please enter a URL to analyze.");
    return;
  }

  // Normalize: prepend https:// if missing
  const url = raw.startsWith("http://") || raw.startsWith("https://")
    ? raw
    : "https://" + raw;

  setLoading(true);
  hideAll();

  try {
    const res = await fetch(`${API_BASE}/scrape`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error: ${res.status}`);
    }

    const data = await res.json();
    renderOutput(data, url);
  } catch (err) {
    showError(err.message || "Network error. Is the backend running?");
  } finally {
    setLoading(false);
  }
}

/* ── Render all output ── */
function renderOutput(data, url) {
  allLinks = data.links || [];

  // Meta bar
  document.getElementById("metaUrl").textContent = url;
  document.getElementById("metaCount").textContent = allLinks.length;

  // AI Analysis
  const aiDiv = document.getElementById("aiAnalysis");
  aiDiv.innerHTML = formatAIAnalysis(data.ai_analysis || "No analysis returned.");

  // Links table
  renderLinksTable(allLinks);

  // Show output
  document.getElementById("output").classList.remove("hidden");
}

/* ── Format AI analysis text into HTML ── */
function formatAIAnalysis(text) {
  // Split by double newline → paragraphs
  const paragraphs = text.split(/\n\n+/).filter(p => p.trim());
  return paragraphs.map(p => {
    // Bold **text**
    const html = p.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    return `<p>${html}</p>`;
  }).join("");
}

/* ── Render links table ── */
function renderLinksTable(links) {
  const tbody = document.getElementById("linksBody");
  tbody.innerHTML = "";

  if (links.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-dim);padding:28px">No links found.</td></tr>`;
    document.getElementById("linkCountLabel").textContent = "0 links";
    return;
  }

  links.forEach((link, i) => {
    const type = classifyLink(link.url);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td><div class="link-text" title="${escHtml(link.text)}">${escHtml(link.text) || "<em style='color:var(--text-dim)'>—</em>"}</div></td>
      <td><div class="link-url" title="${escHtml(link.url)}">${escHtml(link.url)}</div></td>
      <td><span class="link-type type-${type}">${type}</span></td>
      <td><a class="open-link" href="${escHtml(link.url)}" target="_blank" rel="noopener" title="Open link">↗</a></td>
    `;
    tbody.appendChild(tr);
  });

  document.getElementById("linkCountLabel").textContent = `${links.length} links`;
}

/* ── Filter links by search input ── */
function filterLinks() {
  const q = document.getElementById("linkSearch").value.toLowerCase();
  const rows = document.querySelectorAll("#linksBody tr");
  let visible = 0;

  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    if (text.includes(q)) {
      row.style.display = "";
      visible++;
    } else {
      row.style.display = "none";
    }
  });

  const countEl = document.getElementById("filterCount");
  if (q) {
    countEl.textContent = `${visible} matching`;
  } else {
    countEl.textContent = "";
  }
}

/* ── Export links to CSV ── */
function exportCSV() {
  if (!allLinks.length) return;

  const rows = [["#", "Text", "URL", "Type"]];
  allLinks.forEach((link, i) => {
    rows.push([
      i + 1,
      `"${(link.text || "").replace(/"/g, '""')}"`,
      `"${link.url}"`,
      classifyLink(link.url),
    ]);
  });

  const csv = rows.map(r => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "scraped_links.csv";
  a.click();
}

/* ── Classify link type ── */
function classifyLink(url) {
  if (!url || url === "#" || url.startsWith("javascript")) return "other";
  if (url.startsWith("/") || url.startsWith("./") || url.startsWith("../")) return "internal";
  try {
    const input = document.getElementById("urlInput").value;
    const base = new URL(input.startsWith("http") ? input : "https://" + input);
    const target = new URL(url);
    return target.hostname === base.hostname ? "internal" : "external";
  } catch {
    return "other";
  }
}

/* ── UI helpers ── */
function setLoading(on) {
  const btn = document.getElementById("scrapeBtn");
  const loader = document.getElementById("loader");
  if (on) {
    btn.disabled = true;
    btn.querySelector(".btn-text").textContent = "Analyzing";
    loader.classList.remove("hidden");
  } else {
    btn.disabled = false;
    btn.querySelector(".btn-text").textContent = "Analyze";
    loader.classList.add("hidden");
  }
}

function hideAll() {
  document.getElementById("output").classList.add("hidden");
  document.getElementById("errorBox").classList.add("hidden");
}

function showError(msg) {
  const box = document.getElementById("errorBox");
  document.getElementById("errorMsg").textContent = msg;
  box.classList.remove("hidden");
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ── Allow Enter key to trigger scrape ── */
document.getElementById("urlInput").addEventListener("keydown", e => {
  if (e.key === "Enter") scrape();
});