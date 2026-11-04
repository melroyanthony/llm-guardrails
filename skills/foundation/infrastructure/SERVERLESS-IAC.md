# Serverless TypeScript Stack — Terraform IaC Reference

Complete Terraform module reference for a production serverless TypeScript stack:
Lambda + API Gateway v2, Aurora Serverless v2 + RDS Proxy, DynamoDB, ECS Fargate, SQS.

---

## Module Structure

```
infrastructure/terraform/
├── main.tf              # Root module — wires all child modules together
├── variables.tf         # Project-wide input variables
├── outputs.tf           # Key outputs (API URL, ALB DNS, etc.)
├── terraform.tfvars     # Environment-specific values (not committed for prod)
└── modules/
    ├── vpc/             # VPC, subnets, NAT Gateway, security groups
    ├── lambda/          # Lambda functions, API Gateway v2, IAM roles
    ├── aurora/          # Aurora Serverless v2, RDS Proxy, Secrets Manager
    ├── dynamodb/        # Tables, GSIs, TTL, point-in-time recovery
    ├── ecs/             # Fargate cluster, service, ALB, auto-scaling
    └── sqs/             # Queues, DLQ, event source mapping, CloudWatch alarm
```

---

## Root Module

```hcl
# main.tf
terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "serverless-stack/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags { tags = local.common_tags }
}

locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

module "vpc" {
  source              = "./modules/vpc"
  project             = var.project
  environment         = var.environment
  cidr_block          = var.vpc_cidr
  ecs_container_port  = 8080
}

module "dynamodb" {
  source      = "./modules/dynamodb"
  project     = var.project
  environment = var.environment
}

module "aurora" {
  source             = "./modules/aurora"
  project            = var.project
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  aurora_sg_id       = module.vpc.aurora_sg_id
  min_capacity       = var.aurora_min_capacity
  max_capacity       = var.aurora_max_capacity
}

module "sqs" {
  source               = "./modules/sqs"
  project              = var.project
  environment          = var.environment
  queue_names          = var.queue_names
  alert_sns_arn        = aws_sns_topic.alerts.arn
}

# Event source mapping lives at root level (not inside the SQS module)
# so it can reference both the SQS queue ARN and the Lambda function ARN.
resource "aws_lambda_event_source_mapping" "sqs" {
  for_each         = module.sqs.queue_arns
  event_source_arn = each.value
  function_name    = module.lambda.function_arn
  batch_size       = 10
  maximum_batching_window_in_seconds = 5

  # Partial batch failure: only retry failed messages, not entire batch
  function_response_types = ["ReportBatchItemFailures"]

  scaling_config {
    maximum_concurrency = 5
  }
}

module "lambda" {
  source              = "./modules/lambda"
  project             = var.project
  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  lambda_sg_id        = module.vpc.lambda_sg_id
  db_secret_arn       = module.aurora.secret_arn
  db_proxy_endpoint   = module.aurora.proxy_endpoint
  dynamodb_table_arns = module.dynamodb.table_arns
  sqs_queue_arns      = module.sqs.queue_arns
}

module "ecs" {
  source             = "./modules/ecs"
  project            = var.project
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  ecs_sg_id          = module.vpc.ecs_sg_id
  alb_sg_id          = module.vpc.alb_sg_id
  container_image    = var.ecs_container_image
  container_port     = 8080
}

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-${var.environment}-alerts"
}
```

```hcl
# variables.tf
variable "project"     { type = string }
variable "environment" { type = string }
variable "aws_region"  { type = string; default = "us-east-1" }
variable "vpc_cidr"    { type = string; default = "10.0.0.0/16" }
variable "aurora_min_capacity" { type = number; default = 0.5 }
variable "aurora_max_capacity" { type = number; default = 4 }
variable "queue_names" { type = list(string); default = ["jobs"] }
variable "ecs_container_image" { type = string }

variable "frontend_domain" {
  description = "Frontend origin for CORS (include scheme, e.g., https://app.example.com)"
  type        = string
}
```

```hcl
# outputs.tf
output "api_gateway_url"  { value = module.lambda.api_gateway_url }
output "alb_dns_name"     { value = module.ecs.alb_dns_name }
output "db_proxy_endpoint" { value = module.aurora.proxy_endpoint }
```

---

## VPC Module

```hcl
# modules/vpc/main.tf
data "aws_availability_zones" "available" { state = "available" }

resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.cidr_block, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

resource "aws_internet_gateway" "main" { vpc_id = aws_vpc.main.id }

resource "aws_eip" "nat" { count = 1; domain = "vpc" }

# NOTE: Single NAT Gateway is cost-optimized but NOT HA.
# For production, create one NAT Gateway per AZ with per-AZ route tables.
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.main]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Security Groups
resource "aws_security_group" "lambda" {
  name   = "${var.project}-${var.environment}-lambda-sg"
  vpc_id = aws_vpc.main.id
  egress {
    from_port   = 0; to_port = 0; protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "aurora" {
  name   = "${var.project}-${var.environment}-aurora-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 5432; to_port = 5432; protocol = "tcp"
    security_groups = [aws_security_group.lambda.id, aws_security_group.ecs.id]
  }
}

resource "aws_security_group" "alb" {
  name   = "${var.project}-${var.environment}-alb-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 80;  to_port = 80;  protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443; to_port = 443; protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0; to_port = 0; protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs" {
  name   = "${var.project}-${var.environment}-ecs-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = var.ecs_container_port  # 80 for nginx, 3000 for Node.js
    to_port         = var.ecs_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0; to_port = 0; protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

```hcl
# modules/vpc/outputs.tf
output "vpc_id"             { value = aws_vpc.main.id }
output "public_subnet_ids"  { value = aws_subnet.public[*].id }
output "private_subnet_ids" { value = aws_subnet.private[*].id }
output "lambda_sg_id"       { value = aws_security_group.lambda.id }
output "aurora_sg_id"       { value = aws_security_group.aurora.id }
output "ecs_sg_id"          { value = aws_security_group.ecs.id }
output "alb_sg_id"          { value = aws_security_group.alb.id }
```

```hcl
# modules/vpc/variables.tf (excerpt)
variable "ecs_container_port" {
  type        = number
  default     = 80
  description = "Container port exposed by the ECS task (80 for nginx, 3000 for Node.js)"
}
```

---

## Lambda Module

```hcl
# modules/lambda/main.tf

# IAM Role
# NOTE: Simplified starter role. In production, create one IAM role per
# Lambda function with only the permissions it needs.
# See backend-serverless-ts/SKILL.md "IAM Least Privilege Per Function".
resource "aws_iam_role" "lambda" {
  name = "${var.project}-${var.environment}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "lambda-permissions"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["ec2:CreateNetworkInterface", "ec2:DescribeNetworkInterfaces", "ec2:DeleteNetworkInterface"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [var.db_secret_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"]
        Resource = var.dynamodb_table_arns
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Resource = var.sqs_queue_arns
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "api" {
  function_name = "${var.project}-${var.environment}-api"
  role          = aws_iam_role.lambda.arn
  runtime       = "nodejs22.x"
  handler       = "index.handler"  # Same for ESM (.mjs) — Lambda uses filename.export
  filename      = var.lambda_zip_path  # Built by esbuild, uploaded via CI or terraform archive
  timeout       = 30
  memory_size   = 512

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_sg_id]
  }

  environment {
    variables = {
      NODE_ENV          = var.environment
      DB_PROXY_ENDPOINT = var.db_proxy_endpoint
      DB_SECRET_ARN     = var.db_secret_arn
    }
  }

  depends_on = [aws_iam_role_policy.lambda]
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 30
}

# API Gateway v2 (HTTP API)
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project}-${var.environment}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = var.environment == "production" ? [var.frontend_domain] : ["*"]
    allow_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.apigw.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      protocol         = "$context.protocol"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }
}

resource "aws_cloudwatch_log_group" "apigw" {
  name              = "/aws/apigateway/${aws_apigatewayv2_api.main.name}"
  retention_in_days = 30
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
```

```hcl
# modules/lambda/outputs.tf
output "api_gateway_url"      { value = aws_apigatewayv2_api.main.api_endpoint }
output "lambda_function_name" { value = aws_lambda_function.api.function_name }
output "lambda_role_arn"      { value = aws_iam_role.lambda.arn }
output "function_arn"         { value = aws_lambda_function.api.arn }
```

---

## Aurora Serverless v2 Module

```hcl
# modules/aurora/main.tf

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "db" {
  name                    = "${var.project}/${var.environment}/db"
  recovery_window_in_days = var.environment == "production" ? 7 : 0  # 0 = immediate delete in non-prod
}

# When using manage_master_user_password = true, AWS auto-creates a secret
# containing username + password. Use its ARN for RDS Proxy and Lambda.
# The managed secret ARN is available as:
#   aws_rds_cluster.main.master_user_secret[0].secret_arn
#
# This custom secret stores connection metadata (no password — that's in the managed secret).
resource "aws_secretsmanager_secret_version" "db_metadata" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    engine = "postgres"
    host   = aws_rds_cluster.main.endpoint
    port   = 5432
    dbname = var.project
  })
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-${var.environment}"
  subnet_ids = var.private_subnet_ids
}

resource "aws_rds_cluster" "main" {
  cluster_identifier   = "${var.project}-${var.environment}"
  engine               = "aurora-postgresql"
  engine_mode          = "provisioned"
  engine_version       = "16.3"
  database_name        = replace(var.project, "-", "_")
  master_username                 = "dbadmin"
  manage_master_user_password     = true  # AWS manages password — not stored in TF state
  db_subnet_group_name = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.aurora_sg_id]

  serverlessv2_scaling_configuration {
    min_capacity = var.min_capacity  # 0.5 ACU minimum (v2 does NOT scale to zero)
    max_capacity = var.max_capacity  # 4 ACU for moderate load, 16+ for heavy
  }

  backup_retention_period      = 7
  preferred_backup_window      = "03:00-04:00"
  deletion_protection          = var.environment == "production"
  skip_final_snapshot          = var.environment != "production"
  final_snapshot_identifier    = "${var.project}-${var.environment}-final"
  enabled_cloudwatch_logs_exports = ["postgresql"]
}

resource "aws_rds_cluster_instance" "main" {
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version
}

# RDS Proxy — required for Lambda connections (Lambda cold starts = connection spikes)
resource "aws_iam_role" "rds_proxy" {
  name = "${var.project}-${var.environment}-rds-proxy-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "rds_proxy" {
  role = aws_iam_role.rds_proxy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [aws_secretsmanager_secret.db.arn]
    }]
  })
}

resource "aws_db_proxy" "main" {
  name                   = "${var.project}-${var.environment}-proxy"
  debug_logging          = false
  engine_family          = "POSTGRESQL"
  idle_client_timeout    = 1800
  require_tls            = true
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_subnet_ids         = var.private_subnet_ids
  vpc_security_group_ids = [var.aurora_sg_id]

  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "DISABLED"
    secret_arn  = aws_rds_cluster.main.master_user_secret[0].secret_arn  # AWS-managed credentials
  }
}

resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name
  connection_pool_config {
    max_connections_percent      = 100
    max_idle_connections_percent = 50
  }
}

resource "aws_db_proxy_target" "main" {
  db_cluster_identifier = aws_rds_cluster.main.cluster_identifier
  db_proxy_name         = aws_db_proxy.main.name
  target_group_name     = aws_db_proxy_default_target_group.main.name
}
```

```hcl
# modules/aurora/outputs.tf
output "proxy_endpoint"   { value = aws_db_proxy.main.endpoint }
output "cluster_endpoint" { value = aws_rds_cluster.main.endpoint }
output "secret_arn"       { value = aws_secretsmanager_secret.db.arn }
```

---

## DynamoDB Module

```hcl
# modules/dynamodb/main.tf

resource "aws_dynamodb_table" "jobs" {
  name         = "${var.project}-${var.environment}-jobs"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  attribute {
    name = "gsi1pk"
    type = "S"
  }
  attribute {
    name = "gsi1sk"
    type = "S"
  }

  global_secondary_index {
    name            = "GSI1"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery { enabled = true }

  server_side_encryption { enabled = true }
}

resource "aws_dynamodb_table" "idempotency" {
  name         = "${var.project}-${var.environment}-idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "expiration"
    enabled        = true
  }

  point_in_time_recovery { enabled = true }
}
```

```hcl
# modules/dynamodb/outputs.tf
output "jobs_table_name"        { value = aws_dynamodb_table.jobs.name }
output "idempotency_table_name" { value = aws_dynamodb_table.idempotency.name }
output "table_arns" {
  value = [
    aws_dynamodb_table.jobs.arn,
    "${aws_dynamodb_table.jobs.arn}/index/*",
    aws_dynamodb_table.idempotency.arn,
  ]
}
```

---

## ECS Fargate Module

```hcl
# modules/ecs/main.tf

resource "aws_ecs_cluster" "main" {
  name = "${var.project}-${var.environment}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_iam_role" "task_execution" {
  name = "${var.project}-${var.environment}-ecs-execution-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project}-${var.environment}"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "main" {
  family                   = "${var.project}-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu    # 256, 512, 1024, 2048, 4096
  memory                   = var.task_memory # 512–30720 depending on CPU
  execution_role_arn       = aws_iam_role.task_execution.arn

  container_definitions = jsonencode([{
    name      = var.project
    image     = var.container_image
    essential = true
    portMappings = [{ containerPort = var.container_port, protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
    environment = [
      { name = "NODE_ENV", value = var.environment },
      { name = "PORT",     value = tostring(var.container_port) },
    ]
  }])
}

resource "aws_lb" "main" {
  name               = "${var.project}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_sg_id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "main" {
  name        = "${var.project}-${var.environment}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = ""  # Required for production
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

resource "aws_lb_listener" "https" {
  count             = var.certificate_arn != "" ? 1 : 0
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

# Redirect HTTP to HTTPS when certificate is provided
resource "aws_lb_listener_rule" "redirect_http" {
  count        = var.certificate_arn != "" ? 1 : 0
  listener_arn = aws_lb_listener.http.arn
  priority     = 1

  action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
  condition {
    path_pattern { values = ["/*"] }
  }
}

resource "aws_ecs_service" "main" {
  name            = var.project
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_sg_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.main.arn
    container_name   = var.project
    container_port   = var.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

# Auto-scaling
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.main.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.project}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
```

```hcl
# modules/ecs/outputs.tf
output "alb_dns_name"   { value = aws_lb.main.dns_name }
output "cluster_name"   { value = aws_ecs_cluster.main.name }
output "service_name"   { value = aws_ecs_service.main.name }
```

---

## SQS Module

```hcl
# modules/sqs/main.tf

locals {
  queues = { for name in var.queue_names : name => name }
}

resource "aws_sqs_queue" "dlq" {
  for_each = local.queues

  name                      = "${var.project}-${var.environment}-${each.key}-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = { Queue = each.key }
}

resource "aws_sqs_queue" "main" {
  for_each = local.queues

  name                       = "${var.project}-${var.environment}-${each.key}"
  visibility_timeout_seconds = var.visibility_timeout_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = { Queue = each.key }
}

# NOTE: Event source mapping is defined in the ROOT module (not here)
# to avoid circular dependency: sqs module → lambda ARN → sqs queue ARNs.
# See root main.tf for aws_lambda_event_source_mapping.

# Moved to root module:
# resource "aws_lambda_event_source_mapping" "sqs" {
#   for_each                           = module.sqs.queue_arns
#   event_source_arn                   = each.value
#   function_name                      = module.lambda.function_arn
#   batch_size                         = 10
#   maximum_batching_window_in_seconds = 5
#   scaling_config { maximum_concurrency = 5 }
#   function_response_types            = ["ReportBatchItemFailures"]
# }


resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  for_each = local.queues

  alarm_name          = "${var.project}-${var.environment}-${each.key}-dlq-not-empty"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq[each.key].name
  }

  alarm_actions = [var.alert_sns_arn]
  alarm_description = "DLQ ${each.key} has messages — investigate immediately."
}
```

```hcl
# modules/sqs/variables.tf
variable "project"                    { type = string }
variable "environment"                { type = string }
variable "queue_names"                { type = list(string) }
# lambda_function_arn removed — event source mapping lives in root module
variable "visibility_timeout_seconds" { type = number; default = 180 }
variable "max_receive_count"          { type = number; default = 3 }
variable "batch_size"                 { type = number; default = 10 }
variable "batching_window"            { type = number; default = 0 }
variable "max_concurrency"            { type = number; default = 5 }
variable "alert_sns_arn"              { type = string }
```

```hcl
# modules/sqs/outputs.tf
output "queue_urls" {
  value = { for k, q in aws_sqs_queue.main : k => q.url }
}
output "queue_arns" {
  value = { for k, q in aws_sqs_queue.main : k => q.arn }
}
output "dlq_arns" {
  value = { for k, q in aws_sqs_queue.dlq : k => q.arn }
}
```

---

## Security Checklist

- Lambda has no inbound rules — egress only via NAT for outbound calls
- Aurora accepts connections only from `lambda-sg` and `ecs-sg`, never from `0.0.0.0/0`
- ALB terminates TLS (add HTTPS listener with ACM cert for production); ECS listens on plain HTTP inside the VPC
- RDS Proxy enforces TLS (`require_tls = true`) on all DB connections
- Secrets stored in Secrets Manager, never in environment variables
- DynamoDB tables have server-side encryption enabled by default (AWS-managed key)
- IAM roles use least privilege — Lambda can only read/write its own tables
- CloudTrail and VPC Flow Logs should be enabled at the account level (not shown here)
