---
platform: kubernetes
signals: k8s_scheduling
---
# Runbook: Pod stuck in Pending (FailedScheduling)

## Symptoms
Pod stays `Pending`. Events show `FailedScheduling` with `Insufficient cpu`,
`Insufficient memory`, `didn't match Pod's node affinity/selector` or `untolerated taint`.

## Diagnosis
1. Read the scheduler message with `kubectl describe pod <pod> -n <ns>`; the last event explains
   how many nodes were rejected and why.
2. Insufficient resources: compare requests with allocatable capacity using
   `kubectl describe nodes` and the "Allocated resources" block of each node.
3. Affinity/selector mismatch: compare `nodeSelector`/`affinity` in the pod spec with the
   node labels from `kubectl get nodes --show-labels`.
4. Taints: `kubectl describe node <node>` shows Taints; compare with the pod's tolerations.
5. Check whether the cluster autoscaler tried to add a node:
   `kubectl -n kube-system logs deploy/cluster-autoscaler --tail=100`.

## Remediation
- Requests set far above real usage: right-size requests in the Helm values (use `kubectl top`).
- Cluster genuinely full: raise the node group max size through Terraform, not by hand in the console.
- Wrong selector/toleration: fix the manifest in Git and redeploy through the pipeline.

## Escalation
If the autoscaler log shows `max node group size reached` or cloud quota errors, escalate to
the platform team; this needs a capacity or quota change.
