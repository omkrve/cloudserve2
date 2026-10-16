
resource "aws_sns_topic" "alerts" {
  name = "${var.project_prefix}-alerts"
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name        = "${var.project_prefix}-high-cpu"
  alarm_description = "Alert when average EC2 CPU exceeds 80%"

  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  threshold           = 80

  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "missing"

  dimensions = {
    InstanceId = var.instance_id
  }

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = {
    Name = "${var.project_prefix}-high-cpu"
  }
}
