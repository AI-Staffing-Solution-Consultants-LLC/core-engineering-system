"""
Telemetry Listener — GCP Cloud Run and Cloudflare Workers telemetry polling.

Polls GCP Cloud Run service health via the gcloud CLI and (stubbed) Cloudflare
Workers telemetry queue on a configurable interval. Detected anomalies are
written to the tamper-evident ledger as ``type: "telemetry_anomaly"`` entries.

Usage::

    from telemetry import TelemetryListener

    listener = TelemetryListener(
        project="aissc-core-engine-self-dep",
        region="us-central1",
        polling_interval=60,
    )
    listener.start()
    # ... service runs ...
    listener.stop()

Graceful degradation:
    - If the gcloud CLI is not authenticated, logs a warning and continues
      polling (it will retry on the next cycle).
    - If ``subprocess`` times out, logs the error and continues.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("self-remediation.telemetry")

# ── Stub for Cloudflare telemetry ────────────────────────────────────────
# In production this would be replaced with a real Cloudflare Workers
# queue consumer. For now it is a no-op placeholder.
CF_QUEUE_NAME: str = os.environ.get("CF_REMEDIATION_QUEUE", "remediation-events")


class TelemetryListener:
    """Background telemetry poller for GCP Cloud Run and Cloudflare Workers.

    Writes telemetry anomalies into the ledger via the provided ledger writer.
    """

    def __init__(
        self,
        project: str,
        region: str,
        polling_interval: int = 60,
        ledger_writer: Any = None,
    ) -> None:
        """Initialise the telemetry listener.

        Args:
            project: GCP project ID (e.g. ``aissc-core-engine-self-dep``).
            region: GCP region (e.g. ``us-central1``).
            polling_interval: Seconds between poll cycles (default 60).
            ledger_writer: A ``LedgerWriter`` instance (from ``src.ledger``)
                used to persist anomaly events. If ``None``, ledger writes
                are skipped.
        """
        self.project: str = project
        self.region: str = region
        self.polling_interval: int = polling_interval
        self.ledger_writer = ledger_writer
        self._thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._chain_head: str = ""

    # ── Public API ───────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background polling thread.

        If a thread is already running this is a no-op.
        """
        if self._thread is not None and self._thread.is_alive():
            logger.warning("TelemetryListener: polling thread already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._polling_loop,
            name="telemetry-poller",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "TelemetryListener started — project=%s region=%s interval=%ds",
            self.project,
            self.region,
            self.polling_interval,
        )

    def stop(self) -> None:
        """Signal the polling thread to stop and wait for it to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.polling_interval + 10)
            self._thread = None
        logger.info("TelemetryListener stopped")

    # ── Polling loop ─────────────────────────────────────────────────────

    def _polling_loop(self) -> None:
        """Main polling loop — runs in a background daemon thread."""
        while not self._stop_event.is_set():
            try:
                self._poll_gcp()
                self._poll_cloudflare()
            except Exception:
                logger.exception("TelemetryListener: unhandled error in poll cycle")

            # Sleep in 1-second increments so we respond to stop quickly
            deadline = time.monotonic() + self.polling_interval
            while time.monotonic() < deadline:
                if self._stop_event.is_set():
                    return
                time.sleep(min(1.0, deadline - time.monotonic()))

    # ── GCP Cloud Run polling ────────────────────────────────────────────

    def _poll_gcp(self) -> None:
        """Poll GCP Cloud Run services via the gcloud CLI.

        Calls::

            gcloud run services list \\
                --project={self.project} \\
                --region={self.region} \\
                --format=json

        Parses the JSON output and checks each service for non-ready
        conditions. Anomalies are written to the ledger.
        """
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "list",
                    f"--project={self.project}",
                    f"--region={self.region}",
                    "--format=json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            logger.warning(
                "TelemetryListener: gcloud CLI not found — skipping GCP poll"
            )
            return
        except subprocess.TimeoutExpired:
            logger.error("TelemetryListener: gcloud CLI timed out")
            return

        if result.returncode != 0:
            stderr = result.stderr.strip()[:500]
            logger.warning(
                "TelemetryListener: gcloud CLI returned %d — %s",
                result.returncode,
                stderr,
            )
            return

        try:
            services: list[dict] = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.warning("TelemetryListener: failed to parse gcloud JSON output")
            return

        for svc in services:
            service_name = svc.get("metadata", {}).get("name", "unknown")
            conditions: list[dict] = svc.get("status", {}).get("conditions", [])

            for condition in conditions:
                status = condition.get("status", "Unknown")
                if status == "True":
                    # This condition is ready/ok — skip
                    continue

                condition_type = condition.get("type", "Unknown")
                reason = condition.get("reason", "")
                message = condition.get("message", "")

                anomaly = {
                    "source": "gcp_cloud_run",
                    "service_name": service_name,
                    "condition_type": condition_type,
                    "condition_status": status,
                    "condition_reason": reason,
                    "condition_message": message,
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }

                logger.warning(
                    "Telemetry anomaly: %s / %s (%s)",
                    service_name,
                    condition_type,
                    status,
                )

                self._write_anomaly(anomaly)

    # ── Cloudflare telemetry (stub) ──────────────────────────────────────

    def _poll_cloudflare(self) -> None:
        """Placeholder for Cloudflare Workers telemetry queue consumption.

        Reads from the queue identified by ``CF_REMEDIATION_QUEUE`` env var.
        Currently a no-op — this will be wired in a future iteration.
        """
        # Stub: Cloudflare Workers telemetry queue
        # queue_name = CF_QUEUE_NAME
        # In the future this will pull from a Cloudflare Workers queue
        # (e.g. via the Cloudflare API or a Workers binding) and emit
        # telemetry_anomaly entries for failing Workers.
        pass

    # ── Ledger integration ───────────────────────────────────────────────

    def _write_anomaly(self, anomaly: dict) -> None:
        """Write a telemetry anomaly to the tamper-evident ledger.

        Uses the ``LedgerWriter`` instance if available; otherwise logs
        the anomaly as a fallback.
        """
        entry_payload = dict(anomaly)
        entry_payload["queue_name"] = CF_QUEUE_NAME

        if self.ledger_writer is not None:
            try:
                self._chain_head = self.ledger_writer.write(
                    "telemetry_anomaly",
                    entry_payload,
                    self._chain_head,
                )
                logger.info(
                    "Telemetry anomaly ledgered: %s — %s",
                    anomaly.get("service_name"),
                    anomaly.get("condition_type"),
                )
            except Exception:
                logger.exception("TelemetryListener: ledger write failed")
        else:
            logger.info(
                "Telemetry anomaly (no ledger): %s",
                json.dumps(anomaly, default=str),
            )
