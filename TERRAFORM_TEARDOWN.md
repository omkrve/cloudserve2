\# CloudServe — Terraform Teardown Procedure



\## 1. Purpose



This procedure describes how to safely remove the AWS infrastructure provisioned for the CloudServe demonstration project using Terraform.



\*\*Current status:\*\* The CloudServe infrastructure is deployed and operational. The teardown procedure is documented for assignment evidence only. No resources are being deleted as part of this documentation exercise.



\## 2. Resources managed by Terraform



The Terraform plan identifies resources including:



\- VPC, public subnet, internet gateway, and route table

\- EC2 instance and associated security group

\- IAM role, instance profile, and policy attachments

\- Amazon SNS alert topic

\- CloudWatch CPU utilization alarm



The exact resources to be destroyed must be verified from the Terraform configuration and state before execution.



\## 3. Pre-teardown safety checks



1\. Confirm that the demonstration is complete and approval has been obtained to remove the environment.

2\. Confirm the Terraform working directory and AWS account/region.

3\. Back up the Terraform state securely and protect it as sensitive information.

4\. Check whether the EC2 instance contains application data, SQLite databases, uploaded attachments, or other information that must be retained.

5\. Review resources shared with other applications and identify any dependencies.

6\. Run `terraform plan -destroy` and review every proposed deletion.



\## 4. Teardown commands



Run these commands only during an approved cleanup window.



```powershell

terraform init

terraform validate

terraform plan -destroy -out=destroy.tfplan

terraform show destroy.tfplan

```



After reviewing and approving the plan, execute the saved plan:



```powershell

terraform apply destroy.tfplan

```



The apply command can permanently delete infrastructure and associated resources. Do not run it while CloudServe is still needed for demonstration or assessment.



\## 5. Post-teardown verification



After an approved teardown:



\- Confirm that the intended EC2 instance and networking resources were removed.

\- Verify the status of the associated CloudWatch alarm and SNS topic.

\- Check the AWS console for resources that Terraform did not manage.

\- Review the final Terraform state and any AWS billing or cost reports.

\- Retain required project evidence and backups securely.



\## 6. Recovery and configuration consistency



If a deployment or teardown fails, inspect the Terraform output and AWS resource status before retrying. Avoid manual changes that cause configuration drift. Use a fresh Terraform plan to assess the actual state before making further changes.



\## 7. Current execution record



For this assignment evidence exercise, only the Terraform plan and configuration checks were performed. The teardown was documented but \*\*not executed\*\*. The CloudServe environment remains available for demonstration.



