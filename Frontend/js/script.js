/* ============================================================
   WiseGuardian Frontend — Wired to S41 FastAPI Backend
   Production-grade, highly resilient JS application state engine.
   Includes:
   - Infinite reload / loop killer with single-flight deauth lock.
   - Subtabs switching (Health Overview, Savings & Liquidity, Borrowing & Credit).
   - Dedicated User Profile View & PUT /api/users/me management.
   - Robust null / undefined fallbacks across all UI renderers.
   - Clean state teardown & AbortController request cancellation.
   - Cookie & LocalStorage token resolution.
   ============================================================ */

const API_BASE_URL = "http://localhost:8000";

const CONSENT_CATEGORIES = ["income", "expenses", "transactions", "savings", "borrowing"];
const CONSENT_LABELS = {
  income: "Income & Earnings",
  expenses: "Expense Categories",
  transactions: "Transactions",
  savings: "Savings & Liquidity",
  borrowing: "Borrowing Information",
};

// DOM Helpers
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];

/* ------------------------------------------------------------
   Global State & Lifecycle Management
   ------------------------------------------------------------ */
let isDeauthenticating = false;
let eventsInitialized = false;
let currentFetchController = new AbortController();
let loadSequenceId = 0;
let consentState = {}; // category -> consent record or null
let lastBatchToken = null;

/* ------------------------------------------------------------
   Token & Cookie Helpers
   ------------------------------------------------------------ */
function getCookie(name) {
  if (typeof document === "undefined" || !document.cookie) return null;
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, "\\$1") + "=([^;]*)")
  );
  return match ? decodeURIComponent(match[1]) : null;
}

function getToken() {
  try {
    const localToken = localStorage.getItem("wg_token");
    if (localToken && localToken.trim() !== "") return localToken;
  } catch (e) {
    /* localStorage access blocked or restricted */
  }
  return getCookie("wg_token") || getCookie("access_token") || null;
}

function setSession(token, user) {
  try {
    if (token) {
      localStorage.setItem("wg_token", token);
      document.cookie = `wg_token=${encodeURIComponent(token)}; path=/; max-age=86400; SameSite=Lax`;
    }
    if (user) {
      localStorage.setItem("wg_user", JSON.stringify(user));
    }
  } catch (e) {
    console.warn("Storage write error:", e);
  }
}

function getStoredUser() {
  try {
    const raw = localStorage.getItem("wg_user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function clearSession() {
  try {
    localStorage.removeItem("wg_token");
    localStorage.removeItem("wg_user");
  } catch (e) {
    console.warn("Storage clear error:", e);
  }
  document.cookie = "wg_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
}

/* ------------------------------------------------------------
   Session Teardown & Deauth Guard (Kills Infinite Loops)
   ------------------------------------------------------------ */
function teardownSession() {
  if (currentFetchController) {
    currentFetchController.abort();
    currentFetchController = new AbortController();
  }

  if (window.toastTimer) {
    clearTimeout(window.toastTimer);
    window.toastTimer = null;
  }

  consentState = {};
  lastBatchToken = null;

  const avatar = $("#userAvatar");
  if (avatar) avatar.textContent = "--";

  const consentCount = $("#consentCount");
  if (consentCount) consentCount.textContent = "0/5 Consents Granted";

  const csvResult = $("#csvPreviewResult");
  if (csvResult) csvResult.innerHTML = "";

  const csvConfirm = $("#csvConfirmBtn");
  if (csvConfirm) csvConfirm.classList.add("hidden");

  ["#loginForm", "#registerForm", "#chatForm", "#profileForm"].forEach((selector) => {
    const form = $(selector);
    if (form && typeof form.reset === "function") form.reset();
  });
}

function handleDeauthentication(reason = "Session expired. Please log in again.") {
  if (isDeauthenticating) return;
  isDeauthenticating = true;

  try {
    teardownSession();
    clearSession();
    showAuthScreen();
    showToast(reason);
  } finally {
    setTimeout(() => {
      isDeauthenticating = false;
    }, 500);
  }
}

/* ------------------------------------------------------------
   Core API Helper
   ------------------------------------------------------------ */
async function apiFetch(path, { method = "GET", body, isForm = false, signal } = {}) {
  if (isDeauthenticating && path !== "/api/auth/logout") {
    const err = new Error("Session is deauthenticating.");
    err.code = "DEAUTH_IN_PROGRESS";
    throw err;
  }

  const headers = {};
  if (!isForm) headers["Content-Type"] = "application/json";

  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const fetchSignal = signal || currentFetchController.signal;

  let res;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
      signal: fetchSignal,
    });
  } catch (networkErr) {
    if (networkErr.name === "AbortError") {
      const err = new Error("Request cancelled.");
      err.code = "ABORTED";
      throw err;
    }
    throw new Error(
      `Could not reach backend at ${API_BASE_URL}. Ensure FastAPI is running.`
    );
  }

  let envelope = null;
  try {
    envelope = await res.json();
  } catch {
    /* empty response body */
  }

  if (res.status === 401) {
    handleDeauthentication((envelope && envelope.message) || "Session expired. Please log in again.");
    const authErr = new Error((envelope && envelope.message) || "Unauthorized");
    authErr.code = "UNAUTHORIZED";
    throw authErr;
  }

  if (!envelope || envelope.success !== true) {
    const message = (envelope && envelope.message) || `Request failed (HTTP ${res.status}).`;
    const err = new Error(message);
    err.code = (envelope && envelope.error_code) || `HTTP_${res.status}`;
    err.status = res.status;
    throw err;
  }

  return envelope.data;
}

/* ------------------------------------------------------------
   UI Helper Utilities
   ------------------------------------------------------------ */
function showToast(text) {
  if (!text || text === "Request cancelled." || text === "Session is deauthenticating.") return;
  const t = $("#toast");
  if (!t) return;
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => t?.classList.remove("show"), 2600);
}

function showView(id) {
  $$(".view").forEach((v) => v.classList.toggle("hidden", v.id !== id));
  $$(".desktop-nav button,.mobile-nav button").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === id)
  );
  if (id === "profile") {
    loadProfile();
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function switchSubtab(subtabKey) {
  $$(".subtabs button").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.subtab === subtabKey);
  });

  $$("[data-subtab-group]").forEach((el) => {
    const groups = (el.dataset.subtabGroup || "").split(" ");
    if (subtabKey === "all" || groups.includes(subtabKey)) {
      el.classList.remove("hidden");
    } else {
      el.classList.add("hidden");
    }
  });
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s).replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[m]));
}

function inr(n) {
  const val = Number(n);
  if (isNaN(val)) return "₹0";
  return `₹${Math.abs(val).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function showAuthScreen() {
  const shell = $("#appShell");
  const auth = $("#authScreen");
  if (shell) shell.classList.add("hidden");
  if (auth) auth.classList.remove("hidden");
}

function showAppShell() {
  const auth = $("#authScreen");
  const shell = $("#appShell");
  if (auth) auth.classList.add("hidden");
  if (shell) shell.classList.remove("hidden");
}

function showAuthError(id, message) {
  const el = $(id);
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
}

function hideAuthError(id) {
  const el = $(id);
  if (el) el.classList.add("hidden");
}

/* ------------------------------------------------------------
   Event Binding Setup
   ------------------------------------------------------------ */
function setupEventHandlers() {
  if (eventsInitialized) return;
  eventsInitialized = true;

  // View Navigation
  document.addEventListener("click", (e) => {
    const viewBtn = e.target.closest("[data-view]");
    if (viewBtn && viewBtn.dataset.view) {
      showView(viewBtn.dataset.view);
      return;
    }

    const subtabBtn = e.target.closest("[data-subtab]");
    if (subtabBtn && subtabBtn.dataset.subtab) {
      switchSubtab(subtabBtn.dataset.subtab);
      return;
    }

    const explainBtn = e.target.closest("[data-explain]");
    if (explainBtn && explainBtn.dataset.explain) {
      showToast(explainBtn.dataset.explain);
    }
  });

  // Auth tabs
  $$(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".auth-tab").forEach((t) => t.classList.toggle("active", t === tab));
      const showLogin = tab.dataset.authTab === "login";
      $("#loginForm")?.classList.toggle("hidden", !showLogin);
      $("#registerForm")?.classList.toggle("hidden", showLogin);
    });
  });

  // Login form
  $("#loginForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAuthError("#loginError");
    const email = $("#loginEmail")?.value.trim() || "";
    const password = $("#loginPassword")?.value || "";

    if (!email || !password) {
      showAuthError("#loginError", "Please enter both email and password.");
      return;
    }

    try {
      const data = await apiFetch("/api/auth/login-json", {
        method: "POST",
        body: { email, password },
      });
      if (data?.access_token) {
        setSession(data.access_token, data.user);
        await bootApp();
      } else {
        throw new Error("Invalid response from auth server.");
      }
    } catch (err) {
      showAuthError("#loginError", err.message || "Login failed.");
    }
  });

  // Register form
  $("#registerForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAuthError("#registerError");
    const full_name = $("#registerName")?.value.trim() || "";
    const email = $("#registerEmail")?.value.trim() || "";
    const password = $("#registerPassword")?.value || "";
    const user_type = $("#registerType")?.value || "student";

    if (!full_name || !email || !password) {
      showAuthError("#registerError", "All fields are required.");
      return;
    }

    try {
      const data = await apiFetch("/api/auth/register", {
        method: "POST",
        body: { full_name, email, password, user_type },
      });
      if (data?.access_token) {
        setSession(data.access_token, data.user);
        await bootApp();
      } else {
        throw new Error("Registration succeeded but no session token was received.");
      }
    } catch (err) {
      showAuthError("#registerError", err.message || "Registration failed.");
    }
  });

  // Logout button
  $("#logoutBtn")?.addEventListener("click", async () => {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
    } catch {
      /* ignore server logout failures */
    }
    handleDeauthentication("Logged out successfully.");
  });

  // Demo seed button
  $("#seedDemoBtn")?.addEventListener("click", async () => {
    try {
      await apiFetch("/api/demo/seed", { method: "POST" });
      showToast("Demo data loaded successfully.");
      await loadAll();
      showView("dashboard");
    } catch (err) {
      showToast(err.message);
    }
  });

  // Revoke all consents button
  $("#revokeAll")?.addEventListener("click", async () => {
    try {
      const activeRecords = CONSENT_CATEGORIES.map((c) => consentState[c]).filter(
        (r) => r && r.is_active
      );
      if (activeRecords.length === 0) {
        showToast("No active consents to revoke.");
        return;
      }
      await Promise.all(
        activeRecords.map((r) => apiFetch(`/api/consents/${r.id}`, { method: "DELETE" }))
      );
      showToast("All consents revoked.");
      await loadConsents();
      await loadAll();
    } catch (err) {
      showToast(err.message);
    }
  });

  // Profile update form
  $("#profileForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const full_name = $("#editProfileName")?.value.trim();
    const user_type = $("#editProfileType")?.value;

    if (!full_name) {
      showToast("Name cannot be empty.");
      return;
    }

    try {
      const updatedUser = await apiFetch("/api/users/me", {
        method: "PUT",
        body: { full_name, user_type },
      });
      setSession(getToken(), updatedUser);
      updateUserAvatar(updatedUser);
      renderProfile(updatedUser);
      showToast("Profile updated successfully!");
    } catch (err) {
      showToast(err.message);
    }
  });

  // Add transaction
  $("#addTransaction")?.addEventListener("click", async () => {
    const type = $("#txType")?.value || "expense";
    const title = $("#txTitle")?.value.trim() || "";
    const amount = Number($("#txAmount")?.value);
    const category = $("#txCategory")?.value || "Other";
    const date = $("#txDate")?.value || new Date().toISOString().slice(0, 10);

    if (!title || isNaN(amount) || amount <= 0) {
      showToast("Please enter a valid description and positive amount.");
      return;
    }

    try {
      if (type === "income") {
        await apiFetch("/api/financial-data/income", {
          method: "POST",
          body: { source: title, amount, frequency: "one_time", record_date: date },
        });
      } else {
        await apiFetch("/api/financial-data/expenses", {
          method: "POST",
          body: { category, amount, frequency: "one_time", record_date: date },
        });
      }
      if ($("#txTitle")) $("#txTitle").value = "";
      if ($("#txAmount")) $("#txAmount").value = "";
      showToast("Record added successfully.");
      await loadDataView();
      await loadDashboard();
    } catch (err) {
      showToast(err.message);
    }
  });

  // CSV Preview & Confirm
  $("#csvPreviewBtn")?.addEventListener("click", async () => {
    const fileInput = $("#csvFile");
    const file = fileInput?.files?.[0];
    if (!file) {
      showToast("Please choose a CSV file first.");
      return;
    }

    const form = new FormData();
    form.append("file", file);
    form.append("confirm", "false");

    try {
      const preview = await apiFetch("/api/transactions/upload", {
        method: "POST",
        body: form,
        isForm: true,
      });
      lastBatchToken = preview?.batch_token || null;
      const rows = preview?.rows || [];
      const rowsHtml = rows
        .map(
          (r) => `
        <tr class="${r.valid ? "row-valid" : "row-invalid"}">
          <td>${r.row_number ?? "-"}</td>
          <td>${escapeHtml(r.date || "")}</td>
          <td>${escapeHtml(r.description || "")}</td>
          <td>${escapeHtml(r.amount || "")}</td>
          <td>${escapeHtml(r.type || "")}</td>
          <td>${r.valid ? "Valid" : escapeHtml((r.errors || []).join("; "))}</td>
        </tr>`
        )
        .join("");

      const resultContainer = $("#csvPreviewResult");
      if (resultContainer) {
        resultContainer.innerHTML = `
          <p>${preview?.valid_rows ?? 0} valid / ${preview?.total_rows ?? 0} total rows.</p>
          <table>
            <thead><tr><th>#</th><th>Date</th><th>Description</th><th>Amount</th><th>Type</th><th>Status</th></tr></thead>
            <tbody>${rowsHtml}</tbody>
          </table>`;
      }
      $("#csvConfirmBtn")?.classList.toggle("hidden", (preview?.valid_rows ?? 0) === 0);
    } catch (err) {
      showToast(err.message);
    }
  });

  $("#csvConfirmBtn")?.addEventListener("click", async () => {
    if (!lastBatchToken) return;
    const form = new FormData();
    form.append("file", new Blob([""]), "confirm.csv");
    form.append("confirm", "true");
    form.append("batch_token", lastBatchToken);

    try {
      const result = await apiFetch("/api/transactions/upload", {
        method: "POST",
        body: form,
        isForm: true,
      });
      showToast(`${result?.inserted_count ?? 0} transactions stored.`);
      $("#csvConfirmBtn")?.classList.add("hidden");
      if ($("#csvPreviewResult")) $("#csvPreviewResult").innerHTML = "";
      if ($("#csvFile")) $("#csvFile").value = "";
      lastBatchToken = null;
      await loadDataView();
      await loadDashboard();
    } catch (err) {
      showToast(err.message);
    }
  });

  // AI Assistant Chat
  $("#chatForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("#chatInput");
    const q = input?.value?.trim();
    if (!q) return;
    if (input) input.value = "";
    askAssistant(q);
  });

  $$(".suggestions button").forEach((b) =>
    b.addEventListener("click", () => {
      if (b.dataset.question) askAssistant(b.dataset.question);
    })
  );

  window.addEventListener("storage", (e) => {
    if (e.key === "wg_token") {
      if (!e.newValue && getToken() === null) {
        handleDeauthentication("Session ended in another tab.");
      } else if (e.newValue && e.newValue !== e.oldValue) {
        init();
      }
    }
  });
}

/* ------------------------------------------------------------
   Dashboard Data Loaders
   ------------------------------------------------------------ */
async function loadDashboard() {
  await Promise.allSettled([
    loadSummary(),
    loadCashFlow(),
    loadExpenseBreakdown(),
    loadCreditReadiness(),
    loadRecommendations(),
  ]);
}

async function loadSummary() {
  try {
    const s = await apiFetch("/api/analytics/summary");
    if (!s) return;
    const cashflow = Number(s.net_cash_flow) || 0;
    const inc = $("#incomeValue");
    const exp = $("#expenseValue");
    const cf = $("#cashflowValue");
    const sav = $("#savingsValue");

    if (inc) inc.textContent = inr(s.total_income);
    if (exp) exp.textContent = inr(s.total_expenses);
    if (cf) {
      cf.textContent = `${cashflow >= 0 ? "+" : "-"}${inr(cashflow)}`;
      cf.className = cashflow >= 0 ? "positive" : "";
    }
    if (sav) {
      sav.textContent =
        s.savings_rate === null || s.savings_rate === undefined
          ? "—"
          : `${Number(s.savings_rate).toFixed(1)}%`;
    }
  } catch (err) {
    if (err.code === "CONSENT_REQUIRED" || err.code === "CONSENT_REVOKED") {
      if ($("#incomeValue")) $("#incomeValue").textContent = "—";
      if ($("#expenseValue")) $("#expenseValue").textContent = "—";
      if ($("#cashflowValue")) $("#cashflowValue").textContent = "—";
      if ($("#savingsValue")) $("#savingsValue").textContent = "—";
    } else if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") {
      showToast(err.message);
    }
  }
}

async function loadCashFlow() {
  const chartEl = $("#cashflowChart");
  if (!chartEl) return;
  try {
    const cf = await apiFetch("/api/analytics/cash-flow");
    const points = cf?.points || [];
    if (!points.length) {
      chartEl.innerHTML = `<div class="empty-note">No cash-flow history yet. Add income/expense records to view trends.</div>`;
      return;
    }
    const maxVal = Math.max(
      1,
      ...points.flatMap((p) => [Number(p.income) || 0, Number(p.expenses) || 0])
    );
    chartEl.innerHTML = points
      .map((p) => {
        const inc = Number(p.income) || 0;
        const exp = Number(p.expenses) || 0;
        const incHeight = Math.max(4, (inc / maxVal) * 100);
        const expHeight = Math.max(4, (exp / maxVal) * 100);
        return `
        <div class="bar-group" title="${escapeHtml(p.period)}: income ${inr(inc)}, expenses ${inr(exp)}">
          <div class="bar income-bar" style="height:${incHeight}%"></div>
          <div class="bar expense-bar" style="height:${expHeight}%"></div>
        </div>`;
      })
      .join("");
  } catch (err) {
    if (err.code === "CONSENT_REQUIRED" || err.code === "CONSENT_REVOKED") {
      chartEl.innerHTML = `<div class="empty-note">Cash flow data hidden — required consent is revoked.</div>`;
    } else if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") {
      showToast(err.message);
    }
  }
}

async function loadExpenseBreakdown() {
  const target = document.getElementById("expenseCategoryList");
  if (!target) return;
  try {
    const breakdown = await apiFetch("/api/analytics/expenses");
    const categories = breakdown?.categories || [];
    if (!categories.length) {
      target.innerHTML = `<div class="empty-note">No expense records found.</div>`;
      return;
    }
    target.innerHTML = categories
      .map((c) => {
        const amt = Number(c.amount) || 0;
        const pct = Math.min(100, Math.max(0, Number(c.percentage_of_total) || 0));
        return `
        <div class="category">
          <div><span>${escapeHtml(c.category)}</span><b>${inr(amt)}</b></div>
          <div class="progress"><i style="width:${pct}%"></i></div>
        </div>`;
      })
      .join("");
  } catch (err) {
    if (err.code === "CONSENT_REQUIRED" || err.code === "CONSENT_REVOKED") {
      target.innerHTML = `<div class="empty-note">Expense analysis hidden — consent revoked.</div>`;
    } else if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") {
      showToast(err.message);
    }
  }
}

async function loadCreditReadiness() {
  const scoreVal = $("#scoreValue");
  const gauge = document.querySelector(".gauge");
  const badge = document.querySelector(".score-card .badge");
  const grid = document.getElementById("factorGrid");

  try {
    const cr = await apiFetch("/api/credit-readiness");
    const score = Number(cr?.score) || 0;
    if (scoreVal) scoreVal.textContent = score;
    if (gauge)
      gauge.style.background = `conic-gradient(#0d4734 0 ${score}%, #e7ece9 ${score}% 100%)`;

    if (badge) {
      badge.textContent = cr?.rating || "N/A";
      badge.className = "badge good";
    }

    if (grid) {
      const factors = cr?.factors || [];
      grid.innerHTML = factors.length
        ? factors
            .map((f) => {
              const impact = Number(f.impact) || 0;
              const cls = impact >= 0 ? "positive-factor" : "negative-factor";
              const sign = impact >= 0 ? "+" : "";
              return `
            <button class="factor ${cls}" data-explain="${escapeHtml(f.explanation)}">
              <b>${sign}${impact} pts</b><span>${escapeHtml(f.name)}</span><small>${escapeHtml(f.direction)}</small>
            </button>`;
            })
            .join("")
        : `<div class="empty-note">No driving factors calculated yet.</div>`;
    }
  } catch (err) {
    if (err.code === "INSUFFICIENT_DATA") {
      if (scoreVal) scoreVal.textContent = "—";
      if (gauge) gauge.style.background = `conic-gradient(#c8cfca 0 0%, #e7ece9 0% 100%)`;
      if (grid) grid.innerHTML = `<div class="empty-note">${escapeHtml(err.message)}</div>`;
    } else if (err.code === "CONSENT_REQUIRED" || err.code === "CONSENT_REVOKED") {
      if (scoreVal) scoreVal.textContent = "—";
      if (gauge) gauge.style.background = `conic-gradient(#c8cfca 0 0%, #e7ece9 0% 100%)`;
      if (badge) { badge.textContent = "LOCKED"; badge.className = "badge"; }
      if (grid) grid.innerHTML = `<div class="empty-note">Credit Readiness locked — Grant income/expenses consent to calculate score.</div>`;
    } else if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") {
      showToast(err.message);
    }
  }
}

async function loadRecommendations() {
  const list = document.getElementById("recommendationList");
  if (!list) return;
  try {
    const recs = await apiFetch("/api/recommendations");
    if (!Array.isArray(recs) || !recs.length) {
      list.innerHTML = `<div class="empty-note">No recommendations yet — add more financial data for personalized guidance.</div>`;
      return;
    }
    list.innerHTML = recs
      .map(
        (r) => `
      <div class="rec-item">
        <div><b>${escapeHtml(r.category)}</b><p>${escapeHtml(r.message)}</p></div>
      </div>`
      )
      .join("");
  } catch (err) {
    if (err.code === "CONSENT_REQUIRED" || err.code === "CONSENT_REVOKED") {
      list.innerHTML = `<div class="empty-note">Recommendations unavailable — consent revoked.</div>`;
    } else if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") {
      list.innerHTML = `<div class="empty-note">${escapeHtml(err.message)}</div>`;
    }
  }
}

/* ------------------------------------------------------------
   User Profile Loader & Renderer
   ------------------------------------------------------------ */
async function loadProfile() {
  try {
    const me = await apiFetch("/api/users/me");
    if (me) {
      setSession(getToken(), me);
      renderProfile(me);
    }
  } catch (err) {
    const stored = getStoredUser();
    if (stored) renderProfile(stored);
  }
}

function renderProfile(user) {
  if (!user) return;
  const initials = String(user.full_name || "?")
    .split(" ")
    .map((p) => p[0])
    .filter(Boolean)
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const cardAvatar = $("#profileCardAvatar");
  if (cardAvatar) cardAvatar.textContent = initials || "WG";

  const nameDisp = $("#profileNameDisplay");
  if (nameDisp) nameDisp.textContent = user.full_name || "User";

  const emailDisp = $("#profileEmailDisplay");
  if (emailDisp) emailDisp.textContent = user.email || "";

  const typeDisp = $("#profileTypeDisplay");
  if (typeDisp) typeDisp.textContent = (user.user_type || "student").replace("_", " ");

  const idDisp = $("#profileIdDisplay");
  if (idDisp) idDisp.textContent = `#${user.id || "N/A"}`;

  const editName = $("#editProfileName");
  if (editName) editName.value = user.full_name || "";

  const editType = $("#editProfileType");
  if (editType) editType.value = user.user_type || "student";
}

function updateUserAvatar(user) {
  const avatar = $("#userAvatar");
  if (avatar && user && user.full_name) {
    avatar.textContent = String(user.full_name)
      .split(" ")
      .map((p) => p[0])
      .filter(Boolean)
      .join("")
      .slice(0, 2)
      .toUpperCase();
  }
}

/* ------------------------------------------------------------
   Consent Manager Loaders & Toggles
   ------------------------------------------------------------ */
async function loadConsents() {
  try {
    const consents = await apiFetch("/api/consents");
    consentState = {};
    const consentList = Array.isArray(consents) ? consents : [];
    CONSENT_CATEGORIES.forEach((cat) => {
      consentState[cat] = consentList.find((c) => c.data_category === cat) || null;
    });
    renderConsents(consentList);
  } catch (err) {
    if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") showToast(err.message);
  }
}

function renderConsents(allConsents) {
  const grid = document.getElementById("consentGrid");
  const consentList = Array.isArray(allConsents) ? allConsents : [];

  if (grid) {
    grid.innerHTML = CONSENT_CATEGORIES.map((cat) => {
      const record = consentState[cat];
      const checked = record && record.is_active ? "checked" : "";
      return `
      <div class="consent-card">
        <div><b>${escapeHtml(CONSENT_LABELS[cat] || cat)}</b><p>${escapeHtml((record && record.purpose) || "")}</p></div>
        <label class="switch"><input type="checkbox" ${checked} data-consent="${cat}"><i></i></label>
      </div>`;
    }).join("");

    $$("[data-consent]", grid).forEach((input) => {
      input.addEventListener("change", () =>
        toggleConsent(input.dataset.consent, input.checked, input)
      );
    });
  }

  const activeCount = CONSENT_CATEGORIES.filter(
    (c) => consentState[c] && consentState[c].is_active
  ).length;
  const countEl = $("#consentCount");
  if (countEl) countEl.textContent = `${activeCount}/${CONSENT_CATEGORIES.length} Consents Granted`;

  const auditBody = document.getElementById("auditBody");
  if (auditBody) {
    const events = consentList
      .map((c) => ({
        time: c.is_active ? c.granted_at : c.revoked_at || c.granted_at,
        category: c.data_category,
        action: c.is_active ? "Granted" : "Revoked",
      }))
      .filter((e) => e.time)
      .sort((a, b) => new Date(b.time) - new Date(a.time));

    auditBody.innerHTML = events.length
      ? events
          .map(
            (e) => `<tr>
              <td>${new Date(e.time).toLocaleString()}</td>
              <td>${escapeHtml(CONSENT_LABELS[e.category] || e.category)}</td>
              <td>${e.action}</td>
            </tr>`
          )
          .join("")
      : `<tr><td colspan="3">No consent activity recorded yet.</td></tr>`;
  }
}

async function toggleConsent(category, wantActive, inputEl) {
  try {
    if (wantActive) {
      await apiFetch("/api/consents", {
        method: "POST",
        body: { data_category: category },
      });
      showToast(`Consent granted: ${CONSENT_LABELS[category] || category}`);
    } else {
      const record = consentState[category];
      if (record && record.id) {
        await apiFetch(`/api/consents/${record.id}`, { method: "DELETE" });
      }
      showToast(`Consent revoked: ${CONSENT_LABELS[category] || category}`);
    }
    await loadConsents();
    await loadAll();
  } catch (err) {
    if (inputEl) inputEl.checked = !wantActive;
    if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") showToast(err.message);
  }
}

/* ------------------------------------------------------------
   Data & Transactions View Loader
   ------------------------------------------------------------ */
async function loadDataView() {
  try {
    const [bundleRes, txnsRes] = await Promise.allSettled([
      apiFetch("/api/financial-data"),
      apiFetch("/api/transactions"),
    ]);

    const bundle = bundleRes.status === "fulfilled" ? bundleRes.value : {};
    let txns = [];
    if (txnsRes.status === "fulfilled") {
      txns = txnsRes.value;
    } else {
      const err = txnsRes.reason;
      if (err.code !== "CONSENT_REQUIRED" && err.code !== "CONSENT_REVOKED" && err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") {
        showToast(err.message);
      }
    }
    renderRecords(bundle || {}, Array.isArray(txns) ? txns : []);
  } catch (err) {
    if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") showToast(err.message);
  }
}

function renderRecords(bundle, txns) {
  const rows = [];
  const incomeList = Array.isArray(bundle?.income) ? bundle.income : [];
  const expenseList = Array.isArray(bundle?.expenses) ? bundle.expenses : [];
  const txnList = Array.isArray(txns) ? txns : [];

  incomeList.forEach((r) =>
    rows.push({
      date: r.record_date,
      type: "income",
      title: r.source,
      category: "Income",
      amount: r.amount,
    })
  );
  expenseList.forEach((r) =>
    rows.push({
      date: r.record_date,
      type: "expense",
      title: r.category,
      category: r.category,
      amount: r.amount,
    })
  );
  txnList.forEach((r) =>
    rows.push({
      date: r.transaction_date,
      type: r.type,
      title: r.description,
      category: r.category,
      amount: r.amount,
    })
  );

  rows.sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0));

  const body = document.getElementById("transactionBody");
  if (!body) return;

  body.innerHTML = rows.length
    ? rows
        .map(
          (t) => `
      <tr>
        <td>${escapeHtml(t.date || "")}</td>
        <td>${escapeHtml(t.type || "")}</td>
        <td>${escapeHtml(t.title || "")}</td>
        <td>${escapeHtml(t.category || "")}</td>
        <td>${t.type === "income" ? "+" : "-"}${inr(t.amount)}</td>
      </tr>`
        )
        .join("")
    : `<tr><td colspan="5">No records found. Add one above, upload a CSV, or load demo data.</td></tr>`;
}

/* ------------------------------------------------------------
   AI Assistant Helper
   ------------------------------------------------------------ */
function addMessage(text, type) {
  const chat = $("#chat");
  if (!chat) return;
  const el = document.createElement("div");
  el.className = `message ${type}`;
  el.textContent = text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

async function askAssistant(question) {
  addMessage(question, "user");
  try {
    const res = await apiFetch("/api/assistant/chat", {
      method: "POST",
      body: { message: question },
    });
    addMessage(res?.answer || "No response received.", "ai");
  } catch (err) {
    if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") {
      addMessage(err.message || "Failed to contact AI advisor.", "ai");
    }
  }
}

/* ------------------------------------------------------------
   Application Boot & Lifecycle Initializers
   ------------------------------------------------------------ */
async function loadAll() {
  const sequenceId = ++loadSequenceId;
  await Promise.allSettled([loadDashboard(), loadConsents(), loadDataView()]);
  if (sequenceId !== loadSequenceId) {
    /* Superceded by newer load request — discard state updates */
  }
}

async function bootApp() {
  const user = getStoredUser();
  updateUserAvatar(user);
  showAppShell();
  showView("dashboard");
  await loadAll();
}

async function init() {
  const txDate = $("#txDate");
  if (txDate) txDate.value = new Date().toISOString().slice(0, 10);

  setupEventHandlers();

  const token = getToken();
  if (!token) {
    showAuthScreen();
    return;
  }

  try {
    const me = await apiFetch("/api/users/me");
    if (me) {
      setSession(token, me);
      await bootApp();
    } else {
      throw new Error("Invalid profile payload");
    }
  } catch (err) {
    if (err.code !== "ABORTED" && err.code !== "DEAUTH_IN_PROGRESS") {
      clearSession();
      showAuthScreen();
    }
  }
}

// Kick off application
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
