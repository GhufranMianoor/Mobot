const API_BASE =
  window.MOBOT_API_BASE ||
  (window.location.hostname ? `${window.location.protocol}//${window.location.hostname}:8000` : "http://127.0.0.1:8000");

const searchForm = document.getElementById("searchForm");
const queryInput = document.getElementById("queryInput");
const chips = document.getElementById("chips");
const cardTemplate = document.getElementById("phoneCardTemplate");
const knnCheckButton = document.getElementById("knnCheckButton");
const resultMeta = document.getElementById("resultMeta");
const resultsGrid = document.getElementById("resultsGrid");
const diagPanel = document.getElementById("diagPanel");

function renderMeta(data) {
  resultMeta.innerHTML = `
    <p class="summary">${data.summary}</p>
    <p class="subsummary">Tier used: <strong>${data.tier_used}</strong> · NLP: <strong>${data.nlp_source}</strong> · Results: <strong>${data.total_results}</strong></p>
  `;
}

function dealClass(badge) {
  if (badge === "Great Deal") return "is-great";
  if (badge === "Overpriced") return "is-over";
  return "is-fair";
}

function renderResults(data) {
  resultsGrid.innerHTML = "";

  if (!Array.isArray(data.results) || data.results.length === 0) {
    resultsGrid.innerHTML = '<p class="empty-state">No matching phones found. Try widening budget or changing brand constraints.</p>';
    return;
  }

  const fragment = document.createDocumentFragment();

  for (const phone of data.results) {
    const node = cardTemplate.content.cloneNode(true);
    node.querySelector(".phone-name").textContent = phone.name;
    node.querySelector(".phone-specs").textContent = phone.specs;
    node.querySelector(".price").textContent = `Rs. ${Number(phone.price_pkr).toLocaleString()}`;

    const tier = node.querySelector(".tier-pill");
    tier.textContent = `${phone.actual_tier} price`;

    const deal = node.querySelector(".deal-pill");
    deal.textContent = phone.deal_badge;
    deal.classList.add(dealClass(phone.deal_badge));

    const link = node.querySelector(".source-link");
    link.textContent = phone.source;
    link.href = phone.url;

    fragment.appendChild(node);
  }

  resultsGrid.appendChild(fragment);
}

function renderKnnDiagnostics(data) {
  diagPanel.innerHTML = `
    <div class="diag-box">
      <p class="diag-status">${data.all_passed ? "k-NN diagnostic check passed." : "k-NN diagnostic check found mismatches."}</p>
    <p class="diag-title">k-NN diagnostics</p>
    <p class="diag-item">samples: ${data.dataset_samples} · k: ${data.k} · checks passed: ${data.pass_count}/${data.total_checks}</p>
    <p class="diag-item">class mix: Budget ${data.class_distribution.Budget}, Mid-Range ${data.class_distribution["Mid-Range"]}, High-End ${data.class_distribution["High-End"]}, Premium ${data.class_distribution.Premium}</p>
    </div>
  `;

  const box = diagPanel.querySelector(".diag-box");
  if (!box) return;
  if (Array.isArray(data.checks)) {
    for (const check of data.checks) {
      const item = document.createElement("p");
      item.className = "diag-item";
      const marker = check.passed ? "PASS" : "FAIL";
      item.textContent = `${marker}: ${check.name} -> expected ${check.expected}, predicted ${check.predicted} (${Math.round((check.confidence || 0) * 100)}%)`;
      box.appendChild(item);
    }
  }
}

function setSearchingState(isSearching) {
  const button = searchForm.querySelector('button[type="submit"]');
  button.disabled = isSearching;
  button.textContent = isSearching ? "Searching..." : "Search";
}

async function runSearch(query) {
  setSearchingState(true);
  resultMeta.innerHTML = '<p class="summary">Searching...</p>';
  resultsGrid.innerHTML = "";
  diagPanel.innerHTML = "";

  try {
    const response = await fetch(`${API_BASE}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    renderMeta(data);
    renderResults(data);
  } catch (error) {
    resultMeta.innerHTML = '<p class="summary">Server is unavailable. Start backend on http://localhost:8000.</p>';
    console.error(error);
  } finally {
    setSearchingState(false);
  }
}

async function runKnnDiagnostics() {
  diagPanel.innerHTML = '<div class="diag-box"><p class="diag-status">Running k-NN diagnostics...</p></div>';
  try {
    const response = await fetch(`${API_BASE}/knn/diagnostics`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    renderKnnDiagnostics(data);
  } catch (error) {
    diagPanel.innerHTML = '<div class="diag-box"><p class="diag-status">Unable to run k-NN diagnostics right now.</p></div>';
    console.error(error);
  }
}

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim();
  if (!query) return;
  await runSearch(query);
});

knnCheckButton.addEventListener("click", runKnnDiagnostics);

chips.addEventListener("click", (event) => {
  if (!(event.target instanceof HTMLButtonElement)) return;
  const text = event.target.textContent?.trim();
  if (!text) return;
  queryInput.value = text;
  searchForm.requestSubmit();
});

queryInput.focus();
