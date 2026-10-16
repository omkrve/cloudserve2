output "project_name" {
  description = "CloudServe project name"
  value       = local.project_prefix
}

output "aws_region" {
  description = "Configured AWS region"
  value       = var.aws_region
}

output "environment" {
  description = "Selected deployment environment"
  value       = var.environment
}
