"""FastAPI application factory for pktlab-ctrld."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from pktlab_ctrld import __version__
from pktlab_ctrld.app import ControllerRuntime

from .routes_datapath import router as datapath_router
from .routes_health import router as health_router
from .routes_topology import router as topology_router


def create_api_app(controller: ControllerRuntime) -> FastAPI:
    """Create the controller HTTP API application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        controller.start()
        try:
            yield
        finally:
            controller.stop()

    app = FastAPI(
        title="pktlab controller",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.controller = controller
    app.include_router(health_router)
    app.include_router(datapath_router)
    app.include_router(topology_router)
    return app


__all__ = ["create_api_app"]
