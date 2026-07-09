"""Governance service (Tier F) — pipeline health monitoring, incident management, and cost tracing."""

from __future__ import annotations

import httpx
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.governance import PipelineIncident, CostLedger, ServiceHealth
from backend.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class GovernanceService:
    """Orchestrates system reliability, API cost tracking, budget gates, and incident containment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.settings = get_settings()

    async def run_health_checks(self) -> dict[str, Any]:
        """Perform active ping checks on external APIs to record latency and availability."""
        services = {
            "anthropic": "https://api.anthropic.com/v1/messages",
            "elevenlabs": "https://api.elevenlabs.io/v1/voices",
            "gptzero": "https://api.gptzero.me/v2/predict/text",
        }

        results = {}
        for name, url in services.items():
            start_time = datetime.now(timezone.utc)
            is_active = False
            latency = 0
            
            try:
                # We do a simple pre-flight check or request with timeout
                async with httpx.AsyncClient(timeout=3.0) as client:
                    # Use OPTIONS or lightweight GET to check availability without consuming credits
                    response = await client.options(url)
                    latency = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    is_active = response.status_code < 500
            except Exception as e:
                logger.warning("service_health_ping_failed", service=name, error=str(e))
                is_active = False

            # Update or insert ServiceHealth record
            query = select(ServiceHealth).where(ServiceHealth.service_name == name)
            res = await self._session.execute(query)
            health = res.scalar_one_or_none()

            if not health:
                health = ServiceHealth(
                    service_name=name,
                    is_active=is_active,
                    latency_ms=latency,
                    last_check_at=datetime.now(timezone.utc)
                )
                self._session.add(health)
            else:
                health.is_active = is_active
                health.latency_ms = latency
                health.last_check_at = datetime.now(timezone.utc)

            results[name] = {"active": is_active, "latency_ms": latency}

        await self._session.commit()
        logger.info("health_checks_completed", services=results)
        return results

    async def log_api_cost(self, service_name: str, amount_usd: float) -> CostLedger:
        """Record an API transaction expense to the cost ledger."""
        current_period = datetime.now(timezone.utc).strftime("%Y-%m")
        ledger = CostLedger(
            service_name=service_name,
            amount_usd=amount_usd,
            billing_period=current_period,
            recorded_at=datetime.now(timezone.utc)
        )
        self._session.add(ledger)
        await self._session.commit()

        logger.info("cost_logged", service=service_name, cost=amount_usd, period=current_period)
        return ledger

    async def check_budget_gate(self, monthly_budget_limit: float = 200.0) -> bool:
        """
        Evaluate if current month's expenses exceed the safety threshold.
        Halts the pipeline automatically if budget is breached.
        """
        current_period = datetime.now(timezone.utc).strftime("%Y-%m")
        query = select(func.sum(CostLedger.amount_usd)).where(CostLedger.billing_period == current_period)
        res = await self._session.execute(query)
        total_spent = res.scalar() or 0.0

        if total_spent >= monthly_budget_limit:
            logger.error("budget_limit_breached", spent=total_spent, limit=monthly_budget_limit)
            # Log an incident to halt downstream processing
            await self.raise_pipeline_incident(
                stage="budget_gate",
                error_msg=f"Monthly spending limit of ${monthly_budget_limit} has been reached. Current spend: ${total_spent}."
            )
            return False

        logger.info("budget_gate_passed", spent=total_spent, limit=monthly_budget_limit)
        return True

    async def raise_pipeline_incident(self, stage: str, error_msg: str) -> PipelineIncident:
        """Halts pipeline stages by recording an active incident block."""
        incident = PipelineIncident(
            stage=stage,
            error_msg=error_msg,
            status="active"
        )
        self._session.add(incident)
        await self._session.commit()

        logger.error("pipeline_incident_raised", stage=stage, error=error_msg)
        return incident

    async def verify_pipeline_safety(self, stage: str) -> None:
        """
        Safety interceptor called before executing pipeline stages.
        Raises RuntimeError if there are active unresolved incidents.
        """
        query = select(PipelineIncident).where(PipelineIncident.status == "active")
        res = await self._session.execute(query)
        active_incidents = list(res.scalars().all())

        if active_incidents:
            incident_details = "; ".join(f"[{i.stage}] {i.error_msg}" for i in active_incidents)
            logger.critical("safety_check_failed_active_incidents", stage=stage, incidents=incident_details)
            raise RuntimeError(f"Pipeline execution halted. Unresolved incidents: {incident_details}")

        logger.info("safety_check_passed", stage=stage)

    async def resolve_incident(self, incident_id: uuid.UUID) -> dict[str, Any]:
        """Resolve an active pipeline block to resume automation operations."""
        query = select(PipelineIncident).where(PipelineIncident.id == incident_id)
        res = await self._session.execute(query)
        incident = res.scalar_one_or_none()

        if not incident:
            return {"error": "Incident not found"}

        incident.status = "resolved"
        incident.resolved_at = datetime.now(timezone.utc)
        await self._session.commit()

        logger.info("pipeline_incident_resolved", incident_id=str(incident_id), stage=incident.stage)
        return {"status": "resolved", "incident_id": str(incident_id)}
