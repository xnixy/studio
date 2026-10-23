"""Compatibility shim: render queue live events use the shared EventHub."""

from __future__ import annotations

from typing import Any

from app.events.hub import event_hub


class RenderQueueHub:
    """Backward-compatible API used by render_pipeline and ws_renders."""

    async def subscribe(self) -> Any:
        # Workspace-scoped subscribe is preferred; bare subscribe is unsupported.
        # Callers that used the old global queue should migrate to event_hub.subscribe(ws).
        raise RuntimeError("Use event_hub.subscribe(workspace_id) instead of render_queue_hub.subscribe()")

    async def unsubscribe(self, queue: Any) -> None:
        return None

    async def publish(self, event: dict[str, Any]) -> None:
        await event_hub.publish(event)


render_queue_hub = RenderQueueHub()
