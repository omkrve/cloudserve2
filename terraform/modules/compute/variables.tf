
variable "project_prefix" {
  description = "Project and environment name"
  type        = string
}

variable "subnet_id" {
  description = "Public subnet ID"
  type        = string
}

variable "security_group_id" {
  description = "Web security group ID"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}
