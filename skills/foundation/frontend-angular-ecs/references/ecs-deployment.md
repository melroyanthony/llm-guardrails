## ECS Fargate Deployment

See `CONTAINER-SETUP.md` for the full Dockerfile, nginx.conf, and entrypoint script.

### ECS Task Definition (Terraform)

```hcl
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.app_name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  # Small SPA: 512/1024. Medium (SSR or heavy libs): 1024/2048
  cpu                      = 512
  memory                   = 1024

  execution_role_arn = aws_iam_role.ecs_task_execution.arn
  task_role_arn      = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = "${aws_ecr_repository.frontend.repository_url}:${var.image_tag}"
    essential = true

    portMappings = [{ containerPort = 8080, protocol = "tcp" }]

    environment = [
      { name = "API_URL",       value = var.api_gateway_url },
      { name = "ENVIRONMENT",   value = var.environment },
      { name = "APP_VERSION",   value = var.image_tag },
    ]

    # Sensitive values from SSM Parameter Store — not visible in task definition
    secrets = [
      { name = "AUTH_CLIENT_ID", valueFrom = var.auth_client_id_ssm_arn },
    ]

    healthCheck = {
      command     = ["CMD-SHELL", "curl -fsS http://localhost:8080/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60    # Give nginx time to start before health checks run
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.app_name}/frontend"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "frontend"
        "awslogs-create-group"  = "true"
      }
    }

    stopTimeout = 30    # Allows in-flight requests to drain before container stops
  }])
}
```

### ALB Target Group

```hcl
resource "aws_lb_target_group" "frontend" {
  name        = "${var.app_name}-frontend-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"    # Required for Fargate (tasks have VPC IPs, not EC2 instances)

  health_check {
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
    matcher             = "200"
  }

  # Fast drain — 30s is enough for SPA (no long-lived connections)
  deregistration_delay = 30

  stickiness {
    type    = "lb_cookie"
    enabled = false    # Angular is stateless; auth state lives in tokens
  }

  tags = var.common_tags
}
```

## Auto-Scaling

```hcl
resource "aws_appautoscaling_target" "frontend" {
  max_capacity       = 20
  min_capacity       = 2     # Always 2 for AZ redundancy
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Scale on CPU utilization
resource "aws_appautoscaling_policy" "frontend_cpu" {
  name               = "${var.app_name}-frontend-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

# Scale on ALB request count per target
resource "aws_appautoscaling_policy" "frontend_requests" {
  name               = "${var.app_name}-frontend-requests"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 1000.0    # Requests per target per minute
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.frontend.arn_suffix}"
    }
  }
}
```

## Environment Injection: Runtime env.js Pattern

Never bake API URLs or feature flags into the Angular build. Use runtime injection so the same Docker image deploys to dev, staging, and production without rebuilding.

**How it works:**
1. `docker-entrypoint.sh` reads ECS task environment variables at container startup
2. Generates `/usr/share/nginx/html/env.js` containing a `window.__env` object
3. nginx serves `env.js` with `Cache-Control: no-store`
4. `index.html` loads `<script src="/env.js"></script>` before `main.js`
5. Angular reads `window.__env` at bootstrap via `runtime-env.ts`

See `CONTAINER-SETUP.md` for the full implementation.

```typescript
// apps/shell/src/environments/runtime-env.ts
declare global {
  interface Window { __env: RuntimeEnv; }
}

export interface RuntimeEnv {
  API_URL: string;
  AUTH_CLIENT_ID: string;
  ENVIRONMENT: 'development' | 'staging' | 'production';
  APP_VERSION: string;
}

const defaults: RuntimeEnv = {
  API_URL: 'http://localhost:3001',
  AUTH_CLIENT_ID: '',
  ENVIRONMENT: 'development',
  APP_VERSION: 'local',
};

// Safe for SSR (window may be undefined on the server)
export const runtimeEnv: RuntimeEnv =
  typeof window !== 'undefined' && window.__env
    ? window.__env
    : defaults;
```

**Build args vs runtime env:**
- `ARG NODE_ENV=production` in Dockerfile → baked at build time, acceptable
- `ARG API_URL=...` in Dockerfile → wrong, forces image rebuild per environment
- `environment: [{ name: "API_URL", value: "..." }]` in ECS task → correct

