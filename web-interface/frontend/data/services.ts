/**
 * Service Registry — CORRECT port mappings verified against docker-compose.yml.
 *
 * ⚠️ SANITIZATION NOTE:
 * The legacy telemetry dashboard (cloudflare/pages/eim/app.js:353-358) had two bugs:
 *   1. Sheryl was mapped to an incorrect port — actual port is 8083.
 *   2. "Connie — Code Analysis" at port 8083 — does NOT exist. That port
 *      belongs to the Sheryl service. There is no "Connie" service anywhere
 *      in docker-compose.yml.
 *
 * The corrected mapping below reflects the actual running services.
 */

export interface ServiceEntry {
  id: string;
  name: string;
  port: number;
  url: string;
  description: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";

export const SERVICES: ServiceEntry[] = [
  {
    id: "track-a",
    name: "Track A — Control Loop",
    port: 8080,
    url: `${API_BASE}/api/track-a`,
    description: "ReAct planning loop, RAG corpus, hypothesis formation",
  },
  {
    id: "track-b",
    name: "Track B — Actuator",
    port: 8081,
    url: `${API_BASE}/api/track-b`,
    description: "Allowlist-validated sandboxed command execution",
  },
  {
    id: "sheryl",
    name: "Sheryl — Strategy",
    port: 8083,
    url: `${API_BASE}/api/sheryl`,
    description: "Strategic planning, risk assessment, executive decision support",
  },
  {
    id: "aura",
    name: "Aura — Code Analysis",
    port: 8084,
    url: `${API_BASE}/api/aura`,
    description: "Static analysis, code review, vulnerability scanning",
  },
  {
    id: "malory",
    name: "Malory — Monitoring",
    port: 8085,
    url: `${API_BASE}/api/malory`,
    description: "System health monitoring, metrics collection, alerting",
  },
  {
    id: "krieger",
    name: "Krieger — Predictions",
    port: 8086,
    url: `${API_BASE}/api/krieger`,
    description: "Predictive modeling, anomaly detection, trend forecasting",
  },
  {
    id: "self-remediation",
    name: "Self-Remediation Engine",
    port: 8087,
    url: `${API_BASE}/api/self-remediation`,
    description: "Automated incident response and self-healing workflows",
  },
  {
    id: "telegram-bridge",
    name: "Telegram Bridge",
    port: 8088,
    url: `${API_BASE}/api/telegram`,
    description: "Telegram bot integration for chat-based command interface",
  },
];

/**
 * Look up a service by its ID.
 */
export function getService(id: string): ServiceEntry | undefined {
  return SERVICES.find((s) => s.id === id);
}

/**
 * Look up a service by its port number.
 */
export function getServiceByPort(port: number): ServiceEntry | undefined {
  return SERVICES.find((s) => s.port === port);
}
