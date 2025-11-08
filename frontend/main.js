// Central service base – change if your central Flask runs elsewhere
// const CENTRAL_BASE = window.location.origin;
const CENTRAL_BASE = "http://localhost:5000";

let accessToken = null;
let loggedInUserId = null;

// ---------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------

function loadStoredAuth() {
  try {
    const token = localStorage.getItem("dl_access_token");
    const userId = localStorage.getItem("dl_user_id");
    if (token) {
      accessToken = token;
      const loginResult = document.getElementById("loginResult");
      const loginUserInput = document.getElementById("loginUser");
      if (loginResult && userId) {
        loginResult.textContent = `Logged in as ${userId}. You can now search and borrow books.`;
      }
      if (loginUserInput && userId) {
        loginUserInput.value = userId;
      }
    }
  } catch {
    // ignore storage errors
  }
}




async function login() {
  const userInput = document.getElementById("loginUser");
  const resDiv = document.getElementById("loginResult");
  const searchBtn = document.getElementById("loginSearchButton"); // the "Search for a book" button

  if (!userInput || !resDiv) return;

  const user = userInput.value.trim();
  if (!user) {
    resDiv.textContent = "Please enter your library ID.";
    return;
  }

  resDiv.textContent = "Signing you in…";

  try {
    const resp = await fetch(`${CENTRAL_BASE}/api/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_external_id: user })
    });

    if (!resp.ok) {
      // Try to get a clean JSON error, fall back to a generic message
      let msg = `Login failed (${resp.status}). Please check your ID and try again.`;
      try {
        const data = await resp.json();
        if (data && data.error) msg = data.error;
      } catch {
        // response wasn't JSON – ignore and use generic msg
      }

      resDiv.textContent = msg;
      accessToken = null;
      sessionStorage.removeItem("dl_access_token");
      sessionStorage.removeItem("dl_user_id");
      if (searchBtn) {
        searchBtn.disabled = true;
        searchBtn.classList.add("disabled");
      }
      return;
    }

    const data = await resp.json();
    accessToken = data.access_token;

    // remember in this browser so we can re-use on catalog page
    sessionStorage.setItem("dl_access_token", accessToken);
    sessionStorage.setItem("dl_user_id", user);

    resDiv.textContent = `Signed in as ${user}. You can now search and borrow books.`;

    // enable the "Search for a book" button
    if (searchBtn) {
      searchBtn.disabled = false;
      searchBtn.classList.remove("disabled");
    }
  } catch (e) {
    console.error(e);
    resDiv.textContent = "Could not reach the central service. Please try again in a moment.";
    accessToken = null;
  }
}



// ---------------------------------------------------------
// Legacy/demo helpers (not used by the main UI, but kept)
// ---------------------------------------------------------

async function searchBooks() {
  const queryInput = document.getElementById("searchQuery");
  const resDiv = document.getElementById("searchResults");
  if (!queryInput || !resDiv) return;

  if (!accessToken) {
    resDiv.textContent =
      "Please log in on the dashboard before searching and borrowing books.";
    return;
  }

  const query = queryInput.value;
  resDiv.textContent = "Searching...";

  try {
    const url = `${CENTRAL_BASE}/api/global/books?query=${encodeURIComponent(
      query
    )}`;
    const resp = await fetch(url);
    const data = await resp.json();

    if (!Array.isArray(data) || data.length === 0) {
      resDiv.textContent = "No results.";
      return;
    }

    resDiv.textContent = "";
    data.forEach((book) => {
      const lines = [];
      lines.push(`Title: ${book.title}`);
      lines.push(`ISBN: ${book.isbn}`);
      lines.push(`Author: ${book.author || "N/A"}`);
      lines.push("Availability:");
      if (book.branches && book.branches.length > 0) {
        book.branches.forEach((b) => {
          lines.push(
            `  - ${b.branch_code}: ${b.available_copies}/${b.total_copies} available`
          );
        });
      } else {
        lines.push("  (no availability data yet)");
      }
      lines.push("");
      resDiv.textContent += lines.join("\n");
    });
  } catch (e) {
    resDiv.textContent = `Error: ${e}`;
  }
}

async function borrowBook() {
  const isbnInput = document.getElementById("borrowIsbn");
  const branchInput = document.getElementById("borrowBranch");
  const resDiv = document.getElementById("borrowResult");
  if (!isbnInput || !branchInput || !resDiv) return;

  const isbn = isbnInput.value;
  const branch = branchInput.value;

  if (!accessToken) {
    resDiv.textContent =
      "Please log in first on the dashboard to get a borrowing token.";
    return;
  }

  resDiv.textContent = "Borrowing...";

  try {
    const resp = await fetch(`${CENTRAL_BASE}/api/borrow`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`
      },
      body: JSON.stringify({
        isbn: isbn,
        branch_code: branch
      })
    });

    const data = await resp.json();
    resDiv.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    resDiv.textContent = `Error: ${e}`;
  }
}

async function loadLoans() {
  const userInput = document.getElementById("loansUser");
  const resDiv = document.getElementById("loansResult");
  if (!userInput || !resDiv) return;

  const user = userInput.value;
  resDiv.textContent = "Loading loans...";

  try {
    const resp = await fetch(
      `${CENTRAL_BASE}/api/user_loans/${encodeURIComponent(user)}`
    );
    const data = await resp.json();

    if (!Array.isArray(data) || data.length === 0) {
      resDiv.textContent = "No loans found.";
      return;
    }

    const lines = ["Loans:"];
    data.forEach((loan) => {
      lines.push(
        `[${loan.branch}] ${loan.isbn} - ${loan.title} (${loan.status})`
      );
    });
    resDiv.textContent = lines.join("\n");
  } catch (e) {
    resDiv.textContent = `Error: ${e}`;
  }
}

// ---------------------------------------------------------
// Dashboard snapshot (dynamic hero panel)
// ---------------------------------------------------------

function isDashboardPage() {
  const path = window.location.pathname;
  return path === "/" || path.endsWith("/index.html");
}

async function loadDashboardSnapshot() {
  const branchesEl = document.getElementById("stat-branches");
  const titlesEl = document.getElementById("stat-titles");
  const reservationsEl = document.getElementById("stat-reservations");
  const miniTableBody = document.getElementById("mini-table-body");
  const statusPill = document.querySelector(".status-pill");

  try {
    const [branchesResp, booksResp] = await Promise.all([
      fetch(`${CENTRAL_BASE}/api/branches`),
      fetch(`${CENTRAL_BASE}/api/global/books`)
    ]);

    const branches = await branchesResp.json();
    const books = await booksResp.json();

    const branchesCount = Array.isArray(branches) ? branches.length : 0;
    const titlesCount = Array.isArray(books) ? books.length : 0;

    if (branchesEl) branchesEl.textContent = branchesCount;
    if (titlesEl) titlesEl.textContent = titlesCount;
    if (reservationsEl) reservationsEl.textContent = "0"; // placeholder for now

    // mini-branch table
    if (miniTableBody && Array.isArray(branches)) {
      miniTableBody.innerHTML = "";
      branches.slice(0, 3).forEach((b) => {
        const row = document.createElement("div");
        row.className = "mini-table-row";

        const cellName = document.createElement("div");
        cellName.className = "mini-table-cell";
        cellName.textContent = b.name || b.code;

        const cellSync = document.createElement("div");
        cellSync.className = "mini-table-cell";
        cellSync.textContent = "Online";

        const cellStatus = document.createElement("div");
        cellStatus.className = "mini-table-cell";
        const chip = document.createElement("span");
        chip.className = "status-chip ok";
        chip.textContent = "Online";
        cellStatus.appendChild(chip);

        row.appendChild(cellName);
        row.appendChild(cellSync);
        row.appendChild(cellStatus);
        miniTableBody.appendChild(row);
      });
    }

    // Simple health indicator
    if (statusPill) {
      if (branchesCount === 0) {
        statusPill.textContent = "Degraded";
      } else {
        statusPill.textContent = "Healthy";
      }
    }
  } catch (err) {
    console.error("Error loading dashboard snapshot", err);
  }
}

// ---------------------------------------------------------
// Bootstrap on page load
// ---------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Restore any stored auth (for friendly message + later pages)
  loadStoredAuth();

  // Borrow button → scroll to login card
  const borrowCta = document.getElementById("borrow-cta");
  const borrowSection = document.getElementById("borrow-flow");
  if (borrowCta && borrowSection) {
    borrowCta.addEventListener("click", () => {
      borrowSection.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  // Dashboard-specific snapshot
  if (isDashboardPage()) {
    loadDashboardSnapshot().catch((err) =>
      console.error("Dashboard init failed", err)
    );
  }
});
