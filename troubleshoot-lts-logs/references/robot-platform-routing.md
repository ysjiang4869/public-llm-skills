# Robot Platform LTS Routing

Use this reference only for the robot-platform codebase. Keep routing portable: do not depend on one developer's absolute filesystem path.

## Find the service identity

Prefer evidence in this order:

1. The deployable module's `src/main/resources/**/application.yml` value at `spring.application.name`.
2. Repository and module path beneath the robot-platform workspace.
3. Java package namespace.

Path and application name override package name. Some gateway code retains a package namespace from another domain.

## Group mapping

| Code location or application prefix | LTS group |
| --- | --- |
| `robot-business/...` or `robot-business-*` | `robot-business` |
| `robot-cloudbrain/...` or `robot-cloudbrain-*` | `robot-cloudbrain` |
| `robot-signal/...` or `robot-signal-*` | `robot-signal` |

## Configured node mapping

Only select nodes present in the MCP configuration.

| Deployable application/module | LTS node |
| --- | --- |
| `robot-business-device` | `robot-business-device` |
| `robot-business-user` | `robot-business-user` |
| `robot-business-maps` | `robot-business-map` |
| `robot-business-cron` | `robot-business-cron` |
| `robot-business-stats` | `robot-business-status` |
| `robot-cloudbrain-ability` | `robot-cloudbrain-ability` |
| `robot-cloudbrain-executor` | `robot-cloudbrain-executor` |
| `robot-cloudbrain-interaction` | `robot-cloudbrain-interaction` |
| `robot-signal-connector` | `robot-signal-connector` |

The configuration also contains the compatibility spelling `robot-cloudbrain-intreaction`; prefer the correctly spelled `robot-cloudbrain-interaction`.

If a deployable module is not listed, do not fabricate a stream. Trace to configured upstream/downstream services that should contain evidence and state that the missing service has no configured LTS target.

## Cross-service selection

Build a candidate service sequence from code before querying:

- Ordinary business API failures: start with the owning `robot-business-*` service, then follow actual remote clients or messages.
- Command delivery from business code to a robot: query the owning business node and `robot-signal-connector` when code shows the signal path.
- Device/body status or event upload: query `robot-signal-connector` and the consuming business node; add cloudbrain only when the traced code forwards the event there.
- Intelligent interaction: follow the actual path among `robot-cloudbrain-interaction`, `robot-cloudbrain-executor`, and `robot-cloudbrain-ability`, then add business/signal services only when the code crosses those boundaries.

Query in causal order. TIDs are service-local and never support cross-service correlation. A TID found in one node may be used only for a follow-up search in that same node. Connect different services with a narrow time window plus shared command/event type, device or user ID, request fields, payload identifiers, and the direction established from code; label this connection as inferred rather than a distributed trace.
