// Central service base – adjust if your Flask central runs elsewhere
// const CENTRAL_BASE = window.location.origin;
const CENTRAL_BASE = "http://localhost:5000";

// -------------------------------------------------------------
// Helpers: auth + API
// -------------------------------------------------------------
function getAccessToken() {
  try {
    return localStorage.getItem("dl_access_token") || null;
  } catch {
    return null;
  }
}

function getUserId() {
  try {
    return localStorage.getItem("dl_user_id") || null;
  } catch {
    return null;
  }
}

async function fetchCatalog(query) {
  const params = query ? `?query=${encodeURIComponent(query)}` : "";
  const resp = await fetch(`${CENTRAL_BASE}/api/global/books${params}`);
  if (!resp.ok) {
    throw new Error(`Catalog request failed with ${resp.status}`);
  }
  return await resp.json();
}

// -------------------------------------------------------------
// Rendering
// -------------------------------------------------------------
function renderBooks(books) {
  const body = document.getElementById("catalog-rows");
  const countEl = document.getElementById("catalog-count");
  if (!body || !countEl) return;

  body.innerHTML = "";

  if (!Array.isArray(books) || books.length === 0) {
    const row = document.createElement("div");
    row.className = "table-row";
    const cell = document.createElement("div");
    cell.className = "table-cell";
    cell.style.gridColumn = "1 / 5";
    cell.textContent = "No titles found.";
    row.appendChild(cell);
    body.appendChild(row);
    countEl.textContent = "0 titles shown.";
    return;
  }

  books.forEach((book) => {
    const row = document.createElement("div");
    row.className = "table-row";

    // Title
    const cellTitle = document.createElement("div");
    cellTitle.className = "table-cell cell-title";
    cellTitle.textContent = book.title || "(Untitled)";
    row.appendChild(cellTitle);

    // Author
    const cellAuthor = document.createElement("div");
    cellAuthor.className = "table-cell";
    cellAuthor.textContent = book.author || "—";
    row.appendChild(cellAuthor);

    // ISBN
    const cellIsbn = document.createElement("div");
    cellIsbn.className = "table-cell";
    cellIsbn.textContent = book.isbn || "—";
    row.appendChild(cellIsbn);

    // Branches / availability
    const cellBranches = document.createElement("div");
    cellBranches.className = "table-cell branches-cell";

    if (Array.isArray(book.branches) && book.branches.length > 0) {
      book.branches.forEach((b) => {
        const total = b.total_copies ?? 0;
        const avail = b.available_copies ?? 0;

        const pill = document.createElement("button");
        pill.type = "button";
        pill.className = "branch-pill";
        pill.dataset.isbn = book.isbn;
        pill.dataset.branchCode = b.branch_code;
        pill.dataset.totalCopies = String(total);
        pill.dataset.availableCopies = String(avail);
        pill.textContent = `${b.branch_code}: ${avail}/${total} available`;

        if (avail <= 0) {
          pill.classList.add("branch-pill--empty");
          pill.disabled = true;
          pill.title = "No copies available at this branch.";
        } else {
          pill.title = "Click to borrow from this branch.";
          pill.addEventListener("click", onBorrowClick);
        }

        cellBranches.appendChild(pill);
      });
    } else {
      const span = document.createElement("span");
      span.textContent = "No branch availability yet.";
      span.style.fontSize = "11px";
      span.style.color = "var(--text-muted)";
      cellBranches.appendChild(span);
    }

    row.appendChild(cellBranches);
    body.appendChild(row);
  });

  countEl.textContent =
    books.length === 1 ? "1 title shown." : `${books.length} titles shown.`;
}

// -------------------------------------------------------------
// Borrow flow from catalog
// -------------------------------------------------------------
async function onBorrowClick(event) {
  const pill = event.currentTarget;
  const isbn = pill.dataset.isbn;
  const branchCode = pill.dataset.branchCode;
  const statusEl = document.getElementById("catalog-status");

  if (!statusEl) return;

  const token = getAccessToken();
  const userId = getUserId();

  if (!token || !userId) {
    statusEl.textContent =
      "You need to sign in on the Dashboard page before borrowing. Open the Dashboard, log in with your library ID, then come back here and try again.";
    statusEl.className = "catalog-status catalog-status--error";
    return;
  }

  statusEl.textContent = `Placing a loan for ${userId} at ${branchCode}...`;
  statusEl.className = "catalog-status catalog-status--pending";

  try {
    const resp = await fetch(`${CENTRAL_BASE}/api/borrow`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        isbn: isbn,
        branch_code: branchCode
      })
    });

    let payload = {};
    try {
      payload = await resp.json();
    } catch {
      // ignore if not JSON
    }

    if (!resp.ok) {
      const msg =
        payload.error ||
        "We couldn’t complete the borrow request. Please try again in a moment.";
      statusEl.textContent = msg;
      statusEl.className = "catalog-status catalog-status--error";
      return;
    }

    // Success
    const due = payload.due_at
      ? new Date(payload.due_at).toLocaleDateString()
      : "soon";

    statusEl.textContent = `Success! The book has been borrowed from ${branchCode}. Due date: ${due}.`;
    statusEl.className = "catalog-status catalog-status--success";

    // Update the pill’s availability count locally
    let available = parseInt(pill.dataset.availableCopies || "0", 10);
    const total = parseInt(pill.dataset.totalCopies || "0", 10);

    if (available > 0) {
      available -= 1;
      pill.dataset.availableCopies = String(available);
      pill.textContent = `${branchCode}: ${available}/${total} available`;
      if (available === 0) {
        pill.classList.add("branch-pill--empty");
        pill.disabled = true;
        pill.title = "No copies available at this branch.";
      }
    }
  } catch (err) {
    console.error("Borrow failed", err);
    statusEl.textContent =
      "Network error while talking to the central service. Please check that everything is running and try again.";
    statusEl.className = "catalog-status catalog-status--error";
  }
}

// -------------------------------------------------------------
// Search + initial load
// -------------------------------------------------------------
async function loadAndRender(query) {
  const statusEl = document.getElementById("catalog-status");
  if (statusEl) {
    statusEl.className = "catalog-status";
    statusEl.textContent =
      "Loading titles from the central catalog…";
  }

  try {
    const books = await fetchCatalog(query);
    renderBooks(books);

    if (statusEl) {
      const token = getAccessToken();
      if (!token) {
        statusEl.textContent =
          "Browse is open to everyone. To borrow, sign in on the Dashboard, then click a branch badge with available copies.";
      } else {
        statusEl.textContent =
          "You are signed in. Click a branch badge with available copies to borrow a book.";
      }
      statusEl.className = "catalog-status";
    }
  } catch (err) {
    console.error(err);
    if (statusEl) {
      statusEl.textContent =
        "We couldn’t load the catalog. Make sure the central service is running.";
      statusEl.className = "catalog-status catalog-status--error";
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("search-input");
  const button = document.getElementById("search-btn");

  // Initial load (all titles)
  loadAndRender("");

  if (button) {
    button.addEventListener("click", () => {
      const q = input ? input.value.trim() : "";
      loadAndRender(q);
    });
  }

  if (input) {
    // Live filter on Enter
    input.addEventListener("keyup", (e) => {
      if (e.key === "Enter") {
        const q = input.value.trim();
        loadAndRender(q);
      }
    });
  }
});
