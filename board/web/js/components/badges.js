import { element } from "../ui.js";

function normal(value, fallback) {
  return String(value || fallback).toLowerCase().replace(/[^a-z0-9_-]/g, "-");
}

export function badge(label, kind = "neutral") {
  return element("span", `badge badge--${normal(kind, "neutral")}`, label);
}

export function statusBadge(status) {
  const value = normal(status, "pending");
  return badge(value, value);
}

export function priorityBadge(priority) {
  const value = normal(priority, "low");
  return badge(value, value);
}

export function riskBadge(risk) {
  const value = normal(risk, "low");
  return badge(`risk:${String(risk || "unknown")}`, value);
}

export function verifyBadge(value) {
  return badge(`verify:${String(value || "—")}`, "verify");
}
