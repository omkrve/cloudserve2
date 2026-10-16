output "vpc_id" {
  description = "CloudServe VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

output "web_security_group_id" {
  description = "Web security group ID"
  value       = aws_security_group.web.id
}
