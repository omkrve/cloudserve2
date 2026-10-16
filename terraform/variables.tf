variable "project_name" {
  description = "Name of the cloud infrastructure project"
  type        = string
  default     = "cloudserve"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging"], var.environment)
    error_message = "Environment must be dev or staging."
  }
}

variable "aws_region" {
  description = "AWS region for CloudServe"
  type        = string
  default     = "ap-south-1"
}
