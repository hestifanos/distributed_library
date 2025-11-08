const CENTRAL_BASE = "http://localhost:5000"; // same as catalog.js

const branchBody = document.getElementById("branchBody");
const statusEl = document.getElementById("status");

async function loadBranches() {
  statusEl.textContent = "Loading branches…";

  try {
    const resp = await fetch(`${CENTRAL_BASE}/api/branches`);
    if (!resp.ok) {
      const msg = await resp.text();
      statusEl.textContent = `Failed to load branches: ${msg}`;
      return;
    }

    const branches = await resp.json();
    if (!Array.isArray(branches) || branches.length === 0) {
      branchBody.innerHTML = "";
      statusEl.textContent = "No branches registered yet.";
      return;
    }

    // For each branch, we *optionally* ping its health endpoint to get live status
    const rows = [];
    for (const b of branches) {
      rows.push(await buildBranchRow(b));
    }
    branchBody.replaceChildren(...rows);
    statusEl.textContent = `Loaded ${branches.length} branch(es).`;
  } catch (err) {
    statusEl.textContent = `Network error while loading branches: ${err}`;
  }
}

async function buildBranchRow(branch) {
  const tr = document.createElement("tr");

  const tdCode = document.createElement("td");
  tdCode.textContent = branch.code;

  const tdName = document.createElement("td");
  tdName.textContent = branch.name;

  const tdUrl = document.createElement("td");
  tdUrl.textContent = branch.base_url;

  const tdStatus = document.createElement("td");
  const pill = document.createElement("span");
  pill.className = "pill";
  pill.textContent = "Checking…";
  tdStatus.appendChild(pill);

  // Default based on central's is_active flag
  let status = branch.is_active ? "online" : "offline";

  // Try to ping /api/health on the branch for fresher status
  try {
    const resp = await fetch(`${branch.base_url.replace(/\/$/, "")}/api/health`, {
      method: "GET",
      // Branch API health is public in this small project
      // If you protected it, you'd add X-API-Key here.
    });
    if (!resp.ok) {
      status = "degraded";
    } else {
      const json = await resp.json().catch(() => ({}));
      status = json.status === "ok" ? "online" : "degraded";
    }
  } catch {
    status = "offline";
  }

  pill.classList.remove("online", "offline", "degraded");
  if (status === "online") {
    pill.classList.add("online");
    pill.textContent = "Online";
  } else if (status === "degraded") {
    pill.classList.add("degraded");
    pill.textContent = "Degraded";
  } else {
    pill.classList.add("offline");
    pill.textContent = "Offline";
  }

  tr.appendChild(tdCode);
  tr.appendChild(tdName);
  tr.appendChild(tdUrl);
  tr.appendChild(tdStatus);
  return tr;
}

// run on page load
loadBranches();
