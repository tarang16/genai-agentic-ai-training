---
platform: kubernetes
signals: k8s_imagepull
---
# Runbook: ImagePullBackOff / ErrImagePull

## Symptoms
Pod status `ImagePullBackOff` or `ErrImagePull`. Events contain `Failed to pull image`,
`manifest unknown`, `pull access denied` or `unauthorized: authentication required`.

## Diagnosis
1. Read the exact event with `kubectl describe pod <pod> -n <ns>` and copy the image reference.
2. `manifest unknown` / `not found`: the tag does not exist. Check the CI build that should
   have pushed it; a failed or skipped push stage is the usual cause.
3. `unauthorized` / `pull access denied`: the imagePullSecret is missing, expired or in the
   wrong namespace. Check with `kubectl get secret <pull-secret> -n <ns>`.
4. For ECR, registry tokens expire after 12 hours; check the credential refresher job.
5. `i/o timeout` or `no such host`: the node cannot reach the registry; check NAT/egress and DNS.

## Remediation
- Missing tag: re-run the pipeline's build-and-push stage, or point the Deployment at the last
  known-good tag through the pipeline.
- Bad credentials: recreate the pull secret from the vault-managed credential and restart the
  refresher job. Never paste registry passwords into tickets or chat.
- Network: raise with the network team with the node name and the failing registry host.

## Escalation
Escalate to the platform team if more than one namespace is affected; that points to the
registry or cluster egress, not one application.
