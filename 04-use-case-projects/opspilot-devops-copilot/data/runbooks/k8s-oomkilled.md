---
platform: kubernetes
signals: k8s_oomkilled
---
# Runbook: Container OOMKilled (exit code 137)

## Symptoms
`kubectl describe pod` shows `Last State: Terminated, Reason: OOMKilled, Exit Code: 137`.
Pods restart under load; JVM services may log `java.lang.OutOfMemoryError` just before.

## Diagnosis
1. Confirm the kill reason:
   `kubectl get pod <pod> -n <ns> -o jsonpath='{.status.containerStatuses[*].lastState}'`.
2. Compare real usage with the limit: `kubectl top pod <pod> -n <ns> --containers` against
   `resources.limits.memory` in the Deployment.
3. For JVM workloads check that the heap is sized relative to the container, e.g.
   `-XX:MaxRAMPercentage=75`. A fixed `-Xmx` larger than the container limit guarantees OOMKills.
4. Check whether usage grows steadily (leak) or spikes with traffic (under-sized) in the
   memory dashboard for the last 24 hours.

## Remediation
- Under-sized: raise `resources.limits.memory` (and the request to match) in the Helm values
  and deploy through the pipeline. A rule of thumb is p99 usage + 25% headroom.
- JVM heap larger than the limit: set `-XX:MaxRAMPercentage=75` and remove the fixed `-Xmx`.
- Leak: raising the limit only delays the next kill. Capture a heap dump and hand it to the app team.
- Short-term mitigation during an incident: scale out to spread load with
  `kubectl scale deployment/<name> --replicas=<n> -n <ns>` (requires change approval).

## Escalation
If memory grows linearly with time regardless of traffic, treat it as an application leak and
escalate to the owning team with the heap dump and the memory graph.
