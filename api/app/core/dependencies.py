"""Application-level FastAPI dependencies.

This module is the single source of truth for dependencies that don't
fit into request- or session-scoped patterns. Currently exposes the
ServiceFactory singleton.
"""

from __future__ import annotations

from app.services.factory import ServiceFactory, service_factory


def get_service_factory() -> ServiceFactory:
    """Returns the module-level ServiceFactory singleton.

    The singleton manages cached HTTP clients (OpenCost, VictoriaMetrics)
    keyed by cluster_id. Its lifecycle is bound to the FastAPI app via
    the lifespan handler, which calls ``service_factory.aclose_all()`` on
    shutdown.
    """
    return service_factory
