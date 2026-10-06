---
platform: terraform
signals: tf_state_lock, tf_auth, tf_drift
---
# Runbook: Terraform state lock, credentials and drift

## State lock held
Symptom: `Error acquiring the state lock` with a `ConditionalCheckFailedException`, a lock ID,
the user who holds it and when it was created.
Diagnosis: check whether a pipeline run or a colleague is still running `terraform apply`
(look at the `Who` and `Created` fields). A lock older than the longest pipeline run is stale.
Remediation: if, and only if, no run is active, release it with
`terraform force-unlock <LOCK_ID>`. This is a changing action and needs approval; unlocking
during a live apply can corrupt state.

## Cloud credentials invalid or expired
Symptom: `No valid credential sources found`, `ExpiredToken`, `InvalidClientTokenId` (AWS) or
`AuthorizationFailed` (Azure).
Diagnosis: run `aws sts get-caller-identity` (or `az account show`) in the same pipeline step.
Check the OIDC role trust policy or the service principal secret expiry.
Remediation: renew the federated role session or rotate the service principal secret in the vault.
Never hard-code access keys in `provider` blocks or tfvars.

## Drift detected
Symptom: the plan shows `Objects have changed outside of Terraform` or
`has been changed outside of Terraform`.
Diagnosis: `terraform plan -refresh-only` shows exactly what changed; find the console or
script change in CloudTrail / Activity Log.
Remediation: either codify the change in Terraform, or revert it with a reviewed `terraform apply`.
Do not apply blindly; the plan may destroy a manual hotfix someone needs.

## Escalation
Escalate to the cloud platform owner if drift touches IAM, networking or security groups.
