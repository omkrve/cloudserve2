
output "sns_topic_arn" {
  description = "SNS topic ARN for CloudServe alerts"
  value       = aws_sns_topic.alerts.arn
}

output "cpu_alarm_name" {
  description = "CloudWatch CPU alarm name"
  value       = aws_cloudwatch_metric_alarm.high_cpu.alarm_name
}
