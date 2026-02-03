from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import heapq
from collections import deque


@dataclass
class NodeState:
    load: int = 0                  # active requests
    usage: int = 0                 # assignments in last K events (or lifetime)
    active_reqs: Set[str] = None   # requestIds currently active
    version: int = 0               # monotonic counter to invalidate stale heap entries
    registered: bool = True


class AdaptiveRouter:
    """
    Implements Part 1-5 routing:
      key order: (active_load, usage_count, nodeId)
      usage_count:
         - Part 4: lifetime assignments
         - Part 5: assignments in last K events (sliding window of event indices)

    Commands:
      REGISTER nodeId
      UNREGISTER nodeId
      REQUEST requestId
      COMPLETE requestId

    Output:
      - REQUEST:   "<requestId> -> <nodeId>"
      - REASSIGN:  "REASSIGN <requestId> -> <nodeId>"
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, NodeState] = {}
        self.req_to_node: Dict[str, str] = {}

        # Heap entries are (load, usage, nodeId, version_snapshot)
        self.heap: List[Tuple[int, int, str, int]] = []

        # For Part 5 sliding window: deque of (event_index, nodeId) for each assignment
        self.assign_history = deque()

    def _push_heap(self, node_id: str) -> None:
        """Push current node metrics onto heap with a version snapshot."""
        st = self.nodes[node_id]
        heapq.heappush(self.heap, (st.load, st.usage, node_id, st.version))

    def _bump(self, node_id: str) -> None:
        """Increment version and push updated metrics."""
        st = self.nodes[node_id]
        st.version += 1
        self._push_heap(node_id)

    def _pop_best_node(self) -> str:
        """
        Pop the best currently-valid node by (load, usage, nodeId).
        Uses lazy deletion: discard stale or unregistered entries.
        """
        while self.heap:
            load, usage, node_id, ver = heapq.heappop(self.heap)
            st = self.nodes.get(node_id)
            if st is None or not st.registered:
                continue
            if ver != st.version:
                continue
            # Valid snapshot; return node_id
            return node_id
        raise RuntimeError("No registered nodes available to route requests.")

    def _expire_usage(self, event_idx: int, K: Optional[int]) -> None:
        """
        Part 5: usage counts are assignments in the last K events.
        We expire any assignment with index <= event_idx - K.
        """
        if K is None:
            return  # no decay
        cutoff = event_idx - K
        # expire assignments that are outside the window
        while self.assign_history and self.assign_history[0][0] <= cutoff:
            old_idx, node_id = self.assign_history.popleft()
            st = self.nodes.get(node_id)
            # If node was unregistered, it might be gone; ignore.
            if st is None or not st.registered:
                continue
            # Decrement usage and update heap
            st.usage -= 1
            self._bump(node_id)

    def _assign(self, request_id: str, event_idx: int, K: Optional[int], *, is_reassign: bool) -> str:
        """
        Assign request_id to the best node per routing order.
        Updates load, usage, mappings, and heap.
        Returns output line.
        """
        node_id = self._pop_best_node()
        st = self.nodes[node_id]

        # Track request -> node mapping
        self.req_to_node[request_id] = node_id
        st.active_reqs.add(request_id)

        # Update load
        st.load += 1

        # Update usage:
        # - Part 4: increments forever
        # - Part 5: increments but also gets expired via _expire_usage()
        st.usage += 1
        self.assign_history.append((event_idx, node_id))

        # Push updated node state
        self._bump(node_id)

        if is_reassign:
            return f"REASSIGN {request_id} -> {node_id}"
        return f"{request_id} -> {node_id}"

    def process(self, events: List[str], K: Optional[int] = None) -> List[str]:
        """
        Process the event stream and return outputs from REQUEST and REASSIGN events.
        If K is None => Part 4 behavior (no decay).
        If K is int  => Part 5 behavior (sliding window decay).
        """
        out: List[str] = []

        for i, raw in enumerate(events):
            # Before each event, expire old usage contributions (Part 5)
            self._expire_usage(i, K)

            parts = raw.split()
            cmd = parts[0]

            if cmd == "REGISTER":
                node_id = parts[1]
                if node_id in self.nodes and self.nodes[node_id].registered:
                    # If duplicate register, ignore or raise; keeping it strict is better.
                    raise ValueError(f"Node already registered: {node_id}")

                st = NodeState(load=0, usage=0, active_reqs=set(), version=0, registered=True)
                self.nodes[node_id] = st
                self._push_heap(node_id)

            elif cmd == "UNREGISTER":
                node_id = parts[1]
                st = self.nodes.get(node_id)
                if st is None or not st.registered:
                    raise ValueError(f"Node not registered: {node_id}")

                # Snapshot the active requests to reassign
                to_move = list(st.active_reqs)

                # Mark node as unregistered so heap entries become invalid
                st.registered = False

                # Remove mappings for requests first (they'll be reassigned)
                for req_id in to_move:
                    # Remove req->node mapping
                    self.req_to_node.pop(req_id, None)

                # Remove the node from dict (optional); leaving it also works if registered=False.
                # We'll remove to keep state clean.
                del self.nodes[node_id]

                # Reassign each request as if it were a fresh REQUEST
                for req_id in to_move:
                    out.append(self._assign(req_id, i, K, is_reassign=True))

            elif cmd == "REQUEST":
                request_id = parts[1]
                if request_id in self.req_to_node:
                    raise ValueError(f"Duplicate active requestId: {request_id}")
                out.append(self._assign(request_id, i, K, is_reassign=False))

            elif cmd == "COMPLETE":
                request_id = parts[1]
                node_id = self.req_to_node.get(request_id)
                if node_id is None:
                    raise ValueError(f"Complete for unknown or already-completed requestId: {request_id}")

                st = self.nodes.get(node_id)
                if st is None or not st.registered:
                    # In a well-formed stream this shouldn't happen because we reassign active requests
                    raise RuntimeError(f"Request {request_id} mapped to non-registered node {node_id}")

                # Remove request from active tracking
                st.active_reqs.remove(request_id)
                del self.req_to_node[request_id]

                # Decrement load and update heap
                st.load -= 1
                self._bump(node_id)

            else:
                raise ValueError(f"Unknown command: {cmd}")

        return out


# ------------------ Example usage ------------------
if __name__ == "__main__":
    router = AdaptiveRouter()

    events = [
        "REGISTER B",
        "REGISTER A",
        "REQUEST r1",     # should go to A (tie load/usage, lexicographically smallest)
        "REQUEST r2",     # should go to B
        "COMPLETE r1",    # A load back to 0
        "REQUEST r3",     # goes to A again
        "UNREGISTER A",   # r3 must be reassigned to B
    ]

    # Part 4 behavior (no decay)
    print(router.process(events, K=None))
