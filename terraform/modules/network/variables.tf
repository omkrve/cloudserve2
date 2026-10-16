variable "project_prefix" {
  description = "Project and environment name"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR range for the CloudServe VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR range for the public subnet"
  type        = string
  default     = "10.20.1.0/24"
}
