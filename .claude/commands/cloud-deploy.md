---
description: "Generate Infrastructure-as-Code for cloud deployment (Terraform, K8s, Pulumi)"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion
---

# Cloud Deploy

Generate Infrastructure-as-Code configurations for deploying the solution to cloud.

## Input
$ARGUMENTS — Optional: cloud provider (aws/gcp/azure) and IaC tool (terraform/pulumi/k8s). If not specified, will ask.

## Process

1. **Read architecture** from `solution/docs/architecture/`
2. **Determine target**:
   - If $ARGUMENTS specifies provider: use that
   - Otherwise: ask user for cloud provider and IaC tool preference
3. **Spawn cloud-deployer agent** to generate:
   - IaC modules (networking, database, compute, monitoring)
   - Environment configurations (staging, production)
   - Deploy workflow (GitHub Actions with OIDC)
   - Secrets template (`.tfvars.example`)
4. **Validate** generated IaC:
   - Terraform: `terraform validate`
   - K8s: `kubectl --dry-run=client`
5. **Update .gitignore** with infrastructure secret exclusions

## Output
```
solution/infrastructure/
├── terraform/ or k8s/     # IaC configurations
├── environments/          # Per-environment configs
└── .github/workflows/     # Deploy pipeline
```

## Examples
```
/cloud-deploy aws terraform    # AWS with Terraform
/cloud-deploy gcp              # GCP (defaults to Terraform)
/cloud-deploy k8s              # Kubernetes manifests with Kustomize
/cloud-deploy                  # Interactive — asks for preference
```
