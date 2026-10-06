---
platform: jenkins
signals: jenkins_disk, jenkins_scm_auth, jenkins_agent_offline, jenkins_build_tool
---
# Runbook: Jenkins pipeline failures

## Disk full on agent
Symptom: `No space left on device` during checkout, `docker build` or archiving.
Diagnosis: on the agent run `df -h` and `du -sh /var/lib/jenkins/workspace/*`, then
`docker system df`; the Docker layer cache is the usual culprit.
Remediation: enable `buildDiscarder(logRotator(numToKeepStr: '20'))` and `cleanWs()` in the
Jenkinsfile; schedule `docker system prune -af --filter until=72h` on agents (changes the
agent, needs approval). Take the agent offline before cleaning so running builds are not broken.

## SCM checkout authentication failure
Symptom: `Permission denied (publickey)`, `Authentication failed for` or
`Could not read from remote repository` in the checkout stage.
Diagnosis: check which credential ID the job uses (`credentialsId` in the Jenkinsfile or job
config) and whether the deploy key or app password was rotated or revoked in Bitbucket/GitHub.
Test from the agent with `ssh -T git@<host>` using the same key.
Remediation: update the Jenkins credential with the rotated key from the vault. Do not
switch the job to a personal account's credentials.

## Agent offline or no executor
Symptom: `Waiting for next available executor`, `There are no nodes with the label` or
`<agent> is offline`.
Diagnosis: Manage Jenkins, then Nodes; check the agent log for JNLP connection errors and the
agent host for memory/disk pressure. Check that the label in `agent { label '...' }` matches a real node.
Remediation: reconnect or relaunch the agent; fix the label typo in the Jenkinsfile.

## Build tool failure (npm / Maven)
Symptom: `npm ERR!`, `[ERROR] Failed to execute goal`, `BUILD FAILURE`.
Diagnosis: scroll up to the *first* error, not the last. Dependency resolution errors
(`ETIMEDOUT`, `Could not resolve dependencies`) point at the artifact proxy (Nexus/Artifactory);
compiler or test errors point at the commit.
Remediation: for proxy errors check the repository manager health; for code errors notify the
committer from the Changes section. Do not retry blindly.

## Escalation
Escalate to the CI platform team when more than one pipeline fails on the same agent within
an hour.
