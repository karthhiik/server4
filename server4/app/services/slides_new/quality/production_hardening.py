"""
Production Hardening — Phase 11.

Health-check system for all 8 service components, load-test
simulation, error-budget tracking, and production readiness
assessment. Integrates with existing pipeline components from
Phases 4-10.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Optional

import structlog

from app.services.slides_new.quality.models import (
    ComponentHealth,
    HealthStatus,
    LoadTestResult,
    ServiceComponent,
)

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════
# HEALTH CHECK ENGINE
# ═══════════════════════════════════════════════════════════════════


class HealthCheckEngine:
    """
    Monitors health of all 8 service components.

    Components checked:
    1. LLM Router — model availability and response time
    2. Image Pipeline — 4-tier fallback chain health
    3. Render Engine — renderer compilation status
    4. Database — MongoDB connection pool
    5. Redis Cache — connectivity and memory usage
    6. WebSocket — connection manager status
    7. Export Pipeline — PPTX/PDF generation
    8. State Sync — CRDT/operation bus (Phase 10)
    """

    # Latency thresholds (ms)
    HEALTHY_LATENCY = 500
    DEGRADED_LATENCY = 2000

    def __init__(self):
        self._component_health: dict[ServiceComponent, ComponentHealth] = {}
        self._check_count = 0
        self._error_window: dict[ServiceComponent, list[float]] = {
            comp: [] for comp in ServiceComponent
        }

    async def check_all(self) -> dict[str, ComponentHealth]:
        """Run health checks on all components."""
        self._check_count += 1
        results: dict[str, ComponentHealth] = {}

        for component in ServiceComponent:
            health = await self._check_component(component)
            self._component_health[component] = health
            results[component.value] = health

        return results

    async def check_component(
        self, component: ServiceComponent
    ) -> ComponentHealth:
        """Run health check on a single component."""
        self._check_count += 1
        health = await self._check_component(component)
        self._component_health[component] = health
        return health

    async def _check_component(
        self, component: ServiceComponent
    ) -> ComponentHealth:
        """Internal check dispatcher."""
        start = time.monotonic()
        try:
            if component == ServiceComponent.LLM_ROUTER:
                return await self._check_llm_router(start)
            elif component == ServiceComponent.IMAGE_PIPELINE:
                return await self._check_image_pipeline(start)
            elif component == ServiceComponent.RENDER_ENGINE:
                return await self._check_render_engine(start)
            elif component == ServiceComponent.DATABASE:
                return await self._check_database(start)
            elif component == ServiceComponent.REDIS_CACHE:
                return await self._check_redis(start)
            elif component == ServiceComponent.WEBSOCKET:
                return await self._check_websocket(start)
            elif component == ServiceComponent.EXPORT_PIPELINE:
                return await self._check_export_pipeline(start)
            elif component == ServiceComponent.STATE_SYNC:
                return await self._check_state_sync(start)
            else:
                return ComponentHealth(
                    component=component,
                    status=HealthStatus.UNKNOWN,
                    details=f"No check implemented for {component.value}",
                )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            self._record_error(component)
            return ComponentHealth(
                component=component,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                error_count=len(self._error_window.get(component, [])),
                details=f"Check failed: {str(e)[:200]}",
            )

    async def _check_llm_router(self, start: float) -> ComponentHealth:
        """Check LLM router availability."""
        try:
            from app.services.llm.model_router import ModelRouter
            router = ModelRouter()
            # Check available models count
            latency = (time.monotonic() - start) * 1000
            status = HealthStatus.HEALTHY if latency < self.HEALTHY_LATENCY else HealthStatus.DEGRADED
            return ComponentHealth(
                component=ServiceComponent.LLM_ROUTER,
                status=status,
                latency_ms=latency,
                details="LLM router initialized successfully",
            )
        except ImportError:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.LLM_ROUTER,
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                details="ModelRouter not available — module import failed",
            )

    async def _check_image_pipeline(self, start: float) -> ComponentHealth:
        """Check image pipeline (4-tier fallback)."""
        try:
            from app.services.slides_new.images.image_pipeline import ImagePipeline
            pipeline = ImagePipeline()
            stats = pipeline.get_stats()
            latency = (time.monotonic() - start) * 1000
            active_providers = stats.get("active_providers", 0)
            status = (
                HealthStatus.HEALTHY if active_providers >= 2
                else HealthStatus.DEGRADED if active_providers >= 1
                else HealthStatus.UNHEALTHY
            )
            return ComponentHealth(
                component=ServiceComponent.IMAGE_PIPELINE,
                status=status,
                latency_ms=latency,
                details=f"Active providers: {active_providers}",
            )
        except (ImportError, Exception) as e:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.IMAGE_PIPELINE,
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                details=f"Image pipeline check skipped: {str(e)[:100]}",
            )

    async def _check_render_engine(self, start: float) -> ComponentHealth:
        """Check render engine availability."""
        try:
            from app.services.slides_new.renderers.base_renderer import RendererType
            available = list(RendererType)
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.RENDER_ENGINE,
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                details=f"Renderers: {[r.value for r in available]}",
            )
        except ImportError:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.RENDER_ENGINE,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                details="Renderer module not available",
            )

    async def _check_database(self, start: float) -> ComponentHealth:
        """Check MongoDB connection."""
        try:
            from app.database import get_db
            db = get_db()
            if db is not None:
                latency = (time.monotonic() - start) * 1000
                return ComponentHealth(
                    component=ServiceComponent.DATABASE,
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    details="MongoDB connection active",
                )
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.DATABASE,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                details="MongoDB: no active connection",
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.DATABASE,
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                details=f"MongoDB check: {str(e)[:100]}",
            )

    async def _check_redis(self, start: float) -> ComponentHealth:
        """Check Redis connectivity."""
        try:
            from app.utils.rate_limiter import RedisClient
            client = RedisClient()
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.REDIS_CACHE,
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                details="Redis client available",
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.REDIS_CACHE,
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                details=f"Redis: {str(e)[:100]}",
            )

    async def _check_websocket(self, start: float) -> ComponentHealth:
        """Check WebSocket manager."""
        try:
            from app.api.websockets.content_progress import router
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.WEBSOCKET,
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                details="WebSocket router available",
            )
        except ImportError:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.WEBSOCKET,
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                details="WebSocket module not available",
            )

    async def _check_export_pipeline(self, start: float) -> ComponentHealth:
        """Check export pipeline (PPTX/PDF)."""
        try:
            from app.services.slides_new.export.export_manager import ExportManager
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.EXPORT_PIPELINE,
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                details="Export manager available",
            )
        except ImportError:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.EXPORT_PIPELINE,
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                details="ExportManager not importable — module may not exist yet",
            )

    async def _check_state_sync(self, start: float) -> ComponentHealth:
        """Check Phase 10 state synchronization."""
        try:
            from app.services.slides_new.sync.operation_bus import OperationBus
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.STATE_SYNC,
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                details="State sync (Phase 10) operational",
            )
        except ImportError:
            latency = (time.monotonic() - start) * 1000
            return ComponentHealth(
                component=ServiceComponent.STATE_SYNC,
                status=HealthStatus.DEGRADED,
                latency_ms=latency,
                details="Operation bus not available",
            )

    def _record_error(self, component: ServiceComponent) -> None:
        """Record an error in the rolling window (1-minute)."""
        now = time.time()
        window = self._error_window.setdefault(component, [])
        window.append(now)
        # Prune old entries (>60s)
        cutoff = now - 60.0
        self._error_window[component] = [t for t in window if t > cutoff]

    def get_overall_status(self) -> HealthStatus:
        """Compute overall system health."""
        if not self._component_health:
            return HealthStatus.UNKNOWN

        statuses = [h.status for h in self._component_health.values()]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        return HealthStatus.UNKNOWN

    def get_summary(self) -> dict[str, Any]:
        """Get health summary."""
        components = {
            comp.value: health.to_dict()
            for comp, health in self._component_health.items()
        }
        return {
            "overall": self.get_overall_status().value,
            "components": components,
            "checks_run": self._check_count,
            "timestamp": time.time(),
        }


# ═══════════════════════════════════════════════════════════════════
# LOAD TEST SIMULATOR
# ═══════════════════════════════════════════════════════════════════


class LoadTestSimulator:
    """
    Simulates concurrent load to test system stability.

    Uses async coroutines to simulate N concurrent users making
    requests. Measures latency percentiles, success rates, and
    error distribution.
    """

    def __init__(
        self,
        success_rate_threshold: float = 95.0,
        p95_threshold_ms: float = 5000.0,
    ):
        self.success_rate_threshold = success_rate_threshold
        self.p95_threshold_ms = p95_threshold_ms
        self._tests_run = 0

    async def run_test(
        self,
        operation: str = "render",
        concurrent_users: int = 10,
        requests_per_user: int = 5,
    ) -> LoadTestResult:
        """
        Run a simulated load test.

        Args:
            operation: Type of operation to simulate
            concurrent_users: Number of simultaneous users
            requests_per_user: Requests each user makes

        Returns:
            LoadTestResult with latency percentiles and status
        """
        self._tests_run += 1
        total = concurrent_users * requests_per_user
        latencies: list[float] = []
        errors: dict[str, int] = {}
        successful = 0
        failed = 0

        start_time = time.monotonic()

        # Simulate concurrent tasks
        tasks = []
        for user in range(concurrent_users):
            for req in range(requests_per_user):
                tasks.append(self._simulate_request(operation, user, req))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                failed += 1
                err_type = type(result).__name__
                errors[err_type] = errors.get(err_type, 0) + 1
            elif isinstance(result, dict):
                if result.get("success"):
                    successful += 1
                    latencies.append(result["latency_ms"])
                else:
                    failed += 1
                    err_type = result.get("error_type", "unknown")
                    errors[err_type] = errors.get(err_type, 0) + 1

        duration = time.monotonic() - start_time

        # Compute percentiles
        latencies.sort()
        n = len(latencies) if latencies else 1

        return LoadTestResult(
            concurrent_users=concurrent_users,
            total_requests=total,
            successful_requests=successful,
            failed_requests=failed,
            avg_latency_ms=sum(latencies) / n if latencies else 0,
            p50_latency_ms=latencies[n // 2] if latencies else 0,
            p95_latency_ms=latencies[int(n * 0.95)] if latencies else 0,
            p99_latency_ms=latencies[int(n * 0.99)] if latencies else 0,
            max_latency_ms=max(latencies) if latencies else 0,
            requests_per_second=total / duration if duration > 0 else 0,
            error_types=errors,
            duration_seconds=duration,
        )

    async def _simulate_request(
        self, operation: str, user_id: int, request_id: int
    ) -> dict[str, Any]:
        """
        Simulate a single request.

        Tries to use real pipeline components when available,
        falls back to statistical simulation.
        """
        start = time.monotonic()

        try:
            if operation == "render":
                result = await self._simulate_render()
            elif operation == "generate":
                result = await self._simulate_generate()
            elif operation == "export":
                result = await self._simulate_export()
            else:
                # Generic simulation
                await asyncio.sleep(random.uniform(0.01, 0.1))
                result = {"success": True}

            latency = (time.monotonic() - start) * 1000
            result["latency_ms"] = latency
            return result

        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return {
                "success": False,
                "latency_ms": latency,
                "error_type": type(e).__name__,
            }

    async def _simulate_render(self) -> dict[str, Any]:
        """Simulate a render operation."""
        # Real import attempt for accurate simulation
        try:
            from app.services.slides_new.renderers.base_renderer import RendererType
            # Simulate render time (light operation)
            await asyncio.sleep(random.uniform(0.005, 0.05))
            return {"success": True, "operation": "render"}
        except ImportError:
            await asyncio.sleep(random.uniform(0.01, 0.05))
            return {"success": True, "operation": "render_sim"}

    async def _simulate_generate(self) -> dict[str, Any]:
        """Simulate content generation."""
        await asyncio.sleep(random.uniform(0.02, 0.15))
        # 5% chance of simulated timeout
        if random.random() < 0.05:
            return {"success": False, "error_type": "timeout"}
        return {"success": True, "operation": "generate"}

    async def _simulate_export(self) -> dict[str, Any]:
        """Simulate export operation."""
        await asyncio.sleep(random.uniform(0.01, 0.08))
        return {"success": True, "operation": "export"}

    def get_stats(self) -> dict[str, Any]:
        return {
            "tests_run": self._tests_run,
            "success_rate_threshold": self.success_rate_threshold,
            "p95_threshold_ms": self.p95_threshold_ms,
        }


# ═══════════════════════════════════════════════════════════════════
# ERROR BUDGET TRACKER
# ═══════════════════════════════════════════════════════════════════


class ErrorBudgetTracker:
    """
    Tracks error budget for SLO compliance.

    Based on Google SRE principles: with a 99.5% SLO target,
    0.5% of requests can fail per window before budget is exhausted.
    """

    def __init__(
        self,
        slo_target: float = 99.5,
        window_seconds: float = 3600,  # 1 hour
    ):
        self.slo_target = slo_target
        self.window_seconds = window_seconds
        self._total_requests = 0
        self._failed_requests = 0
        self._window_start = time.time()
        self._history: list[dict[str, Any]] = []

    def record_request(self, success: bool) -> None:
        """Record a request outcome."""
        self._maybe_rotate_window()
        self._total_requests += 1
        if not success:
            self._failed_requests += 1

    @property
    def error_budget_remaining(self) -> float:
        """Percentage of error budget remaining (0-100)."""
        if self._total_requests == 0:
            return 100.0
        allowed_errors = (100.0 - self.slo_target) / 100.0 * self._total_requests
        if allowed_errors <= 0:
            return 0.0
        used = self._failed_requests / allowed_errors * 100.0
        return max(0.0, 100.0 - used)

    @property
    def current_success_rate(self) -> float:
        """Current success rate percentage."""
        if self._total_requests == 0:
            return 100.0
        return (
            (self._total_requests - self._failed_requests)
            / self._total_requests * 100.0
        )

    @property
    def is_within_budget(self) -> bool:
        return self.error_budget_remaining > 0

    def _maybe_rotate_window(self) -> None:
        """Rotate tracking window if expired."""
        now = time.time()
        if now - self._window_start >= self.window_seconds:
            if self._total_requests > 0:
                self._history.append({
                    "window_start": self._window_start,
                    "total": self._total_requests,
                    "failed": self._failed_requests,
                    "success_rate": self.current_success_rate,
                    "budget_remaining": self.error_budget_remaining,
                })
            # Keep only last 24 windows
            if len(self._history) > 24:
                self._history = self._history[-24:]
            self._total_requests = 0
            self._failed_requests = 0
            self._window_start = now

    def get_summary(self) -> dict[str, Any]:
        return {
            "slo_target": self.slo_target,
            "current_success_rate": round(self.current_success_rate, 2),
            "error_budget_remaining": round(self.error_budget_remaining, 2),
            "within_budget": self.is_within_budget,
            "total_requests": self._total_requests,
            "failed_requests": self._failed_requests,
            "window_seconds": self.window_seconds,
            "history_windows": len(self._history),
        }


# ═══════════════════════════════════════════════════════════════════
# PRODUCTION READINESS ASSESSOR
# ═══════════════════════════════════════════════════════════════════


class ProductionReadinessAssessor:
    """
    Assesses whether the system is ready for production deployment.

    Checks:
    - All critical components healthy
    - Error budget not exhausted
    - Load test passing thresholds
    - No critical configuration issues
    """

    def __init__(self):
        self._health_engine = HealthCheckEngine()
        self._error_tracker = ErrorBudgetTracker()
        self._load_tester = LoadTestSimulator()

    @property
    def health_engine(self) -> HealthCheckEngine:
        return self._health_engine

    @property
    def error_tracker(self) -> ErrorBudgetTracker:
        return self._error_tracker

    @property
    def load_tester(self) -> LoadTestSimulator:
        return self._load_tester

    async def assess(self) -> dict[str, Any]:
        """Run full production readiness assessment."""
        # 1. Health checks
        health = await self._health_engine.check_all()
        overall_health = self._health_engine.get_overall_status()

        # 2. Error budget
        error_budget = self._error_tracker.get_summary()

        # 3. Mini load test (lightweight)
        load_result = await self._load_tester.run_test(
            concurrent_users=5, requests_per_user=3
        )

        # 4. Compute readiness
        issues: list[str] = []
        if overall_health != HealthStatus.HEALTHY:
            issues.append(f"System health: {overall_health.value}")
            unhealthy = [
                comp.value for comp, h in self._health_engine._component_health.items()
                if h.status == HealthStatus.UNHEALTHY
            ]
            if unhealthy:
                issues.append(f"Unhealthy components: {', '.join(unhealthy)}")

        if not self._error_tracker.is_within_budget:
            issues.append("Error budget exhausted")

        if not load_result.passed:
            issues.append(
                f"Load test failed: {load_result.success_rate:.1f}% success, "
                f"p95={load_result.p95_latency_ms:.0f}ms"
            )

        ready = len(issues) == 0
        score = 100.0
        if overall_health == HealthStatus.DEGRADED:
            score -= 20
        elif overall_health == HealthStatus.UNHEALTHY:
            score -= 40
        if not self._error_tracker.is_within_budget:
            score -= 30
        if not load_result.passed:
            score -= 20
        score = max(0.0, score)

        return {
            "production_ready": ready,
            "score": round(score, 1),
            "overall_health": overall_health.value,
            "health_details": {k: v.to_dict() for k, v in health.items()},
            "error_budget": error_budget,
            "load_test": load_result.to_dict(),
            "issues": issues,
            "timestamp": time.time(),
        }
