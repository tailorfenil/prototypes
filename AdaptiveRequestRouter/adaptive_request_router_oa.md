# Adaptive Request Router (OA Problem Statement)

## Overview
You are asked to implement an **in-memory adaptive request router** that processes a sequence of events.
The router assigns incoming requests to nodes based on dynamic routing rules that evolve across multiple parts.

This problem is designed to evaluate:
- State modeling under evolving constraints
- Efficient routing with mutable priorities
- Correct handling of invalidation and reassignment
- Incremental updates with sliding-window constraints

All operations are assumed to run in a **single-threaded environment**.

---

## Input

You are given:
- A list of strings `events[]`, where each string represents a command.
- An integer `K` (used only in Part 5).

Each command is one of the following:

```
REGISTER <nodeId>
UNREGISTER <nodeId>
REQUEST <requestId>
COMPLETE <requestId>
```

- `nodeId` and `requestId` are non-empty strings of lowercase letters and digits.
- Commands must be processed **in the given order**.

---

## Output

Return a list of strings representing outputs produced by routing events.

Output is produced only for:
- `REQUEST`
- Reassignments triggered by `UNREGISTER`

---

## Definitions

- **Active request**: A request that has been assigned to a node and has not yet been completed.
- **Current load of a node**: Number of active requests assigned to that node.
- **Usage count of a node**: Number of times the node has been selected to handle a request.

---

## Part 1 — Basic Routing

### Rules

1. A node must be **registered** before it can receive requests.
2. On `REQUEST requestId`:
   - Assign the request to the node with the **lowest current load**.
   - If multiple nodes have the same load, choose the node with the **lexicographically smallest `nodeId`**.
3. Output format:
   ```
   <requestId> -> <nodeId>
   ```

### Guarantees
- At least one node is registered before any `REQUEST`.

---

## Part 2 — Request Completion

Extend Part 1.

### Rules

1. On `COMPLETE requestId`:
   - Mark the request as completed.
   - Decrement the load of the node handling that request.
2. Each request is completed **exactly once**.

### Performance Requirement
- Routing decisions must be made in **O(log N)** time, where `N` is the number of registered nodes.

---

## Part 3 — Node Removal and Reassignment

Extend Part 2.

### Rules

1. On `UNREGISTER nodeId`:
   - The node is immediately removed.
   - All active requests assigned to that node must be **reassigned**.
2. Each reassignment:
   - Uses the same routing rules as `REQUEST`.
   - Is processed **one request at a time**, updating routing state after each reassignment.
3. Output format for each reassignment:
   ```
   REASSIGN <requestId> -> <newNodeId>
   ```

---

## Part 4 — Usage-Aware Routing

Extend Part 3.

### Additional Rules

1. Each node maintains a **usage count**:
   - Incremented every time a request is assigned to the node (including reassignments).
2. Routing priority is now:
   1. Lowest current load
   2. Lowest usage count
   3. Lexicographically smallest `nodeId`

---

## Part 5 — Sliding Window Usage Decay

Extend Part 4.

### Additional Rules

1. Usage count only includes assignments that occurred within the **last `K` events**.
2. Assignments older than `K` events **no longer contribute** to usage count.
3. Usage decay must be handled **incrementally**; global recomputation is not allowed.

---

## Performance Requirements

Let:
- `N` = number of registered nodes
- `R` = number of active requests on an unregistered node

| Operation   | Required Time Complexity |
|------------|--------------------------|
| REGISTER   | O(log N) |
| REQUEST    | O(log N) |
| COMPLETE   | O(log N) |
| UNREGISTER | O(R log N) |

---

## Notes

- The order in which requests from an unregistered node are reassigned is not specified.
- The router must not rebalance existing assignments except when required by `UNREGISTER`.
- You may assume the input is well-formed unless otherwise stated.

---

## What This Problem Evaluates

- Correct abstraction and state design
- Handling of cascading invalidation
- Efficient priority maintenance
- Incremental reasoning under sliding-window constraints
