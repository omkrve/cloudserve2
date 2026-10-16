
output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.main.id
}

output "public_ip" {
  description = "Public IP of the CloudServe server"
  value       = aws_instance.main.public_ip
}

output "instance_role_arn" {
  description = "IAM role ARN attached to the EC2 instance"
  value       = aws_iam_role.ec2_ssm.arn
}
