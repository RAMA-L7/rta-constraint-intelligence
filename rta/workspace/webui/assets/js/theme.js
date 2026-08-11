/* ═══════════════════════════════════════════════════════════════════════════
   Ṛta — theme.js
   Escaping + status metadata + design tokens.
   Single source of truth: ui/theme.py (served via GET /api/design).
   This module provides a safe fallback so the UI never renders a bare
   unknown status, and every user-controlled value is escaped at render time.
   ═══════════════════════════════════════════════════════════════════════════ */

export function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function escAttr(value) {
  return esc(value);
}

/* Fallback status metadata — mirrors ui/theme.py exactly so the UI is never
   empty if /api/design is slow; the API response replaces it when it arrives. */
const FALLBACK = {
  severity: {
    fatal:   { label: "FATAL",   color: "error",  shape: "octagon" },
    error:   { label: "ERROR",   color: "error",  shape: "octagon" },
    warning: { label: "WARNING", color: "warning", shape: "triangle" },
    info:    { label: "INFO",    color: "info",   shape: "circle" },
  },
  trust: {
    VALIDATED:              { label: "VALIDATED",  color: "success", shape: "square" },
    PARTIALLY_VALIDATED:    { label: "PARTIAL",    color: "warning", shape: "square-half" },
    NETLIST_REQUIRED:       { label: "NETLIST",    color: "info",    shape: "square-net" },
    TCL_EXECUTION_REQUIRED: { label: "TCL EXEC",   color: "unknown", shape: "square-term" },
    UNSUPPORTED:            { label: "UNSUPPORTED", color: "error",  shape: "slash" },
    NOT_VALIDATED:          { label: "NOT CHECKED", color: "unknown", shape: "square-hollow" },
  },
  readiness: {
    READY:                 { label: "READY",   color: "success", shape: "shield" },
    READY_WITH_ADVISORIES: { label: "READY+",  color: "success", shape: "shield-dot" },
    REVIEW_REQUIRED:       { label: "REVIEW",  color: "warning", shape: "triangle" },
    BLOCKED:               { label: "BLOCKED", color: "error",   shape: "octagon" },
    INSUFFICIENT_CONTEXT:  { label: "LIMITED", color: "unknown", shape: "shield-hollow" },
    NOT_APPLICABLE:        { label: "N/A",     color: "muted",   shape: "square-hollow" },
  },
  diff: {
    NEW:       { label: "NEW",       color: "success", shape: "diamond" },
    RESOLVED:  { label: "RESOLVED",  color: "info",    shape: "circle" },
    CHANGED:   { label: "CHANGED",   color: "warning", shape: "triangle" },
    UNCHANGED: { label: "UNCHANGED", color: "muted",   shape: "square" },
  },
  pass_fail: {
    PASS: { label: "PASS", color: "success", shape: "circle" },
    FAIL: { label: "FAIL", color: "error",   shape: "octagon" },
  },
};

const COLOR_MAP = {
  success: "sev-success", warning: "sev-warning", error: "sev-error",
  info: "sev-info", unknown: "sev-unknown", muted: "sev-muted",
};

export const STATUS = { ...FALLBACK };

export function setStatusMeta(meta) {
  /* Replace fallback metadata with the API single source of truth. */
  if (!meta) return;
  for (const kind of ["severity", "trust", "readiness", "diff", "pass_fail"]) {
    if (meta[kind] && typeof meta[kind] === "object") {
      STATUS[kind] = { ...STATUS[kind], ...meta[kind] };
    }
  }
}

export function statusMeta(kind, status) {
  const table = STATUS[kind] || {};
  const s = String(status == null ? "" : status).toUpperCase();
  if (table[s]) return table[s];
  return { label: status == null || status === "" ? "—" : String(status), color: "muted", shape: "square" };
}

export function statusBadge(kind, status) {
  const m = statusMeta(kind, status);
  const color = COLOR_MAP[m.color] || "sev-muted";
  const shape = m.shape || "square";
  const shapeCls = shape.includes("tri") ? "tri"
    : shape.includes("circ") ? "circ"
    : shape.includes("diam") ? "diam" : "";
  return `<span class="sdc-status ${color}"><span class="sh ${shapeCls}"></span>${esc(m.label)}</span>`;
}

export function severityClass(sev) {
  return COLOR_MAP[(STATUS.severity[sev] || {}).color] || "sev-muted";
}

/* Tokens (mirror ui/theme.COLORS) — set from /api/design when available. */
export const TOKENS = {
  colors: {
    background_primary: "#FFFFFF", background_secondary: "#F6F6F6",
    surface: "#FFFFFF", surface_elevated: "#FFFFFF", surface_overlay: "#FFFFFF",
    border_subtle: "#EAEAEA", border_active: "#D4D4D4",
    text_primary: "#18181B", text_secondary: "#3F3F46", text_muted: "#71717A",
    accent_primary: "#111111", accent_secondary: "#2563EB",
    success: "#2F6E4E", warning: "#8A6C14", error: "#A8453A", info: "#2563EB",
    unknown: "#71717A", not_applicable: "#9CA3AF", focus: "#2563EB",
    diff_new: "#2F6E4E", diff_resolved: "#2563EB", diff_changed: "#8A6C14",
    diff_unchanged: "#9CA3AF",
  },
};

export function setTokens(meta) {
  if (meta && meta.colors) Object.assign(TOKENS.colors, meta.colors);
}

export function color(name) {
  return TOKENS.colors[name] || "#68738A";
}
