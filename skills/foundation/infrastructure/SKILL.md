---
name: infrastructure
description: |
  Infrastructure-as-Code patterns for AWS, GCP, and Azure with Terraform, Kubernetes, and secrets management.
  Use when generating IaC configurations, deployment pipelines, or cloud infrastructure.
  Triggers on: "Terraform", "Kubernetes", "IaC", "infrastructure", "AWS", "GCP", "Azure", "deploy".
---

# Infrastructure-as-Code Patterns

## Provider Decision Matrix

| Factor | AWS | GCP | Azure |
|--------|-----|-----|-------|
| Container hosting | ECS Fargate | Cloud Run | Container Apps |
| Managed DB | RDS PostgreSQL | Cloud SQL | Azure Database |
| CDN | CloudFront | Cloud CDN | Azure CDN |
| Secrets | Secrets Manager | Secret Manager | Key Vault |
| Container registry | ECR | Artifact Registry | ACR |
| CI/CD auth | OIDC via IAM | Workload Identity | OIDC via Entra ID |
| Cost (small app) | $30-50/mo | $20-40/mo | $30-50/mo |

## Terraform Module Patterns

### Module Structure
Each module follows this pattern:
```
modules/{name}/
├── main.tf          # Resources
├── variables.tf     # Input variables with validation
├── outputs.tf       # Output values for other modules
└── data.tf          # Data sources (optional)
```

### Networking Module (VPC/VNet)
```hcl
# modules/networking/main.tf
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "${var.project_name}-${var.environment}-vpc" }
}

resource "aws_subnet" "public" {
  count                   = length(var.availability_zones)
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "${var.project_name}-public-${count.index}" }
}

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 100)
  availability_zone = var.availability_zones[count.index]

  tags = { Name = "${var.project_name}-private-${count.index}" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
}
```

### Database Module (RDS)
```hcl
# modules/database/main.tf
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-${var.environment}"
  engine         = "postgres"
  engine_version = "16"
  instance_class = var.instance_class

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  multi_az            = var.environment == "production"
  skip_final_snapshot = var.environment != "production"

  backup_retention_period = var.environment == "production" ? 7 : 1

  tags = { Name = "${var.project_name}-${var.environment}-db" }
}

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}/${var.environment}/db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db.result
}
```

### Compute Module (ECS Fargate)
```hcl
# modules/compute/main.tf
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = var.backend_image
      essential = true

      portMappings = [{ containerPort = 8000, protocol = "tcp" }]

      environment = [
        { name = "ENVIRONMENT", value = var.environment }
      ]

      secrets = [
        { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.db_url.arn }
      ]

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.environment == "production" ? 2 : 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }
}
```

## Kubernetes Patterns

### Deployment
```yaml
# k8s/base/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  labels:
    app: backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: backend:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: database-url
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

### Kustomize Overlays
```yaml
# k8s/overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: production
bases:
  - ../../base
patches:
  - path: patches/backend-replicas.yaml
  - path: patches/resource-limits.yaml
```

## Security Best Practices

### OIDC Authentication (GitHub Actions → Cloud)
```yaml
# No long-lived credentials needed
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::${{ secrets.AWS_ACCOUNT_ID }}:role/github-actions
    aws-region: us-east-1
```

### Terraform State Security
- Remote backend (S3/GCS/Azure Blob) with encryption
- State locking (DynamoDB/GCS/Azure Blob lease)
- Separate state per environment
- Restrict state access to CI/CD and admins only

### Secret Rotation
- Database passwords: use `random_password` + Secrets Manager
- API keys: rotate on deploy, store in secret manager
- TLS certificates: use ACM/Let's Encrypt with auto-renewal

## Cost Optimization

| Service | Staging | Production |
|---------|---------|-----------|
| Compute | 1 instance, smallest | 2+ instances, right-sized |
| Database | Single-AZ, smallest | Multi-AZ, sized for workload |
| NAT Gateway | Shared | Dedicated per AZ |
| CDN | Optional | Required |
| Monitoring | Basic | Full with alerting |

## When NOT to Use
- **Serverless TypeScript on AWS**: Use `infrastructure/SERVERLESS-IAC.md` for Lambda + Aurora + DynamoDB + ECS + SQS Terraform
- **Simple static sites**: Use S3 + CloudFront — Terraform is overkill
- **Local development only**: Use Docker Compose, not Terraform
- **Single developer prototype**: Use cloud console or CDK for rapid iteration

## Environment Promotion Flow

```
Feature Branch → PR → main → Staging (auto) → Production (manual approval)
```

Each environment has:
- Separate Terraform state
- Separate secret store
- Separate container registry tags
- Separate DNS entries
