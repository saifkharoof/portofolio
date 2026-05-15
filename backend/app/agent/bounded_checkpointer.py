"""Bounded in-memory checkpointer that evicts old threads to prevent memory leaks."""

from collections import OrderedDict
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger


class BoundedMemorySaver(MemorySaver):
    """
    A thin wrapper around LangGraph's MemorySaver that caps the number of
    concurrent threads stored in memory.  When the limit is exceeded, the
    least-recently-used thread is evicted entirely.

    This prevents unbounded RAM growth on long-running portfolio servers
    where each visitor spawns a new thread that would otherwise live forever.
    """

    def __init__(self, *, max_threads: int = 50, **kwargs):
        super().__init__(**kwargs)
        self.max_threads = max_threads
        # OrderedDict tracks access order: most-recent at the end
        self._thread_order: OrderedDict[str, bool] = OrderedDict()

    def _touch_thread(self, thread_id: str) -> None:
        """Move thread_id to the end (most-recently-used)."""
        self._thread_order.pop(thread_id, None)
        self._thread_order[thread_id] = True

    def _maybe_evict(self) -> None:
        """Evict the oldest thread if we're over the limit."""
        while len(self._thread_order) > self.max_threads:
            old_thread, _ = self._thread_order.popitem(last=False)
            # Remove all checkpoints for this thread from the internal storage
            keys_to_remove = [
                k for k in self.storage.keys()
                if k[0] == old_thread  # storage keys are (thread_id, checkpoint_ns, checkpoint_id)
            ]
            for k in keys_to_remove:
                del self.storage[k]
            # Also remove from writes storage
            write_keys_to_remove = [
                k for k in self.writes.keys()
                if k[0] == old_thread
            ]
            for k in write_keys_to_remove:
                del self.writes[k]
            logger.debug(f"Evicted thread '{old_thread}' ({len(keys_to_remove)} checkpoints freed)")

    def put(self, config, checkpoint, metadata, new_versions):
        thread_id = config["configurable"].get("thread_id", "")
        self._touch_thread(thread_id)
        result = super().put(config, checkpoint, metadata, new_versions)
        self._maybe_evict()
        return result

    async def aput(self, config, checkpoint, metadata, new_versions):
        thread_id = config["configurable"].get("thread_id", "")
        self._touch_thread(thread_id)
        result = await super().aput(config, checkpoint, metadata, new_versions)
        self._maybe_evict()
        return result
