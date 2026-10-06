---
platform: kubernetes
signals: k8s_crashloop, k8s_probe
---
# Runbook: Pod stuck in CrashLoopBackOff

## Symptoms
`kubectl get pods` shows STATUS `CrashLoopBackOff` and the RESTARTS count keeps rising.
Events show `Back-off restarting failed container`. The service behind the pod returns
502/503 because no ready endpoints exist.

## Diagnosis
1. Read the logs of the *previous* container, not the current one — the current one has
   usually just started: `kubectl logs <pod> -n <ns> --previous`.
2. Check the exit code and reason with `kubectl describe pod <pod> -n <ns>` and look at
   `Last State: Terminated`. Exit code 1 is an application error, 137 is OOMKilled
   (see the OOMKilled runbook), 143 is SIGTERM (usually a failing liveness probe).
3. If logs show a missing config value or `connection refused` to a dependency, compare the
   pod's environment with the ConfigMap/Secret: `kubectl get configmap <name> -n <ns> -o yaml`.
4. If the container exits before writing any log, the entrypoint or command is wrong. Check
   `spec.containers[].command` and `args` in the Deployment.
5. Liveness probe failures (`Liveness probe failed`) with exit code 143 mean the probe is
   killing a healthy-but-slow container. Compare `initialDelaySeconds` with the real startup time.

## Remediation
- Application error after a new release: roll back the Deployment with
  `kubectl rollout undo deployment/<name> -n <ns>`, then fix forward in the pipeline.
- Missing configuration: correct the ConfigMap/Secret in Git and let the GitOps/CI pipeline
  apply it. Do not `kubectl edit` in production; the change will be overwritten.
- Probe too aggressive: raise `initialDelaySeconds` or add a `startupProbe`; ship via the pipeline.
- After the fix, confirm with `kubectl rollout status deployment/<name> -n <ns>`.

## Escalation
Escalate to the owning application team if the previous-container logs show an application
stack trace. Platform on-call owns the case only when the failure is in the node, CNI or
image registry.
