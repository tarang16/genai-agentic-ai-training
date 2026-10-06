---
platform: any
signals: tls_expired, dns_resolution
---
# Runbook: TLS certificate and DNS resolution failures

## Expired or untrusted certificate
Symptom: `x509: certificate has expired or is not yet valid`, `certificate verify failed` or
`CERT_HAS_EXPIRED` from a client, pipeline step or ingress.
Diagnosis: check the served certificate's dates with
`openssl s_client -connect <host>:443 -servername <host>` piped to `openssl x509 -noout -dates`.
For cert-manager: `kubectl get certificate -A` and `kubectl describe certificate <name> -n <ns>`.
Remediation: renew through cert-manager or the certificate authority; find out why auto-renewal
failed (ACME challenge, DNS validation). Never set `insecureSkipVerify` or `curl -k` as a fix.

## DNS resolution failure
Symptom: `Could not resolve host`, `no such host`, `Temporary failure in name resolution`.
Diagnosis: from the failing pod or agent run `nslookup <host>`; in Kubernetes check CoreDNS with
`kubectl -n kube-system logs -l k8s-app=kube-dns --tail=50`. Confirm the record exists in the zone.
Remediation: fix the record or the resolver config; restart CoreDNS only with approval.

## Escalation
Escalate to the network team when resolution fails for more than one zone.
