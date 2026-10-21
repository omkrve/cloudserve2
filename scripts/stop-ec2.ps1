
$instanceIds = @(
    "i-0e6a4b3f5d1f67638"
    "i-08e1887cba1be9abf"
)

$region = "ap-south-1"

foreach ($instanceId in $instanceIds) {

    Write-Host "`nChecking EC2 instance: $instanceId"

    $status = aws ec2 describe-instances `
        --instance-ids $instanceId `
        --region $region `
        --query "Reservations[0].Instances[0].State.Name" `
        --output text

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to get status for $instanceId" -ForegroundColor Red
        continue
    }

    if ($status -eq "stopped") {
        Write-Host "$instanceId is already stopped." -ForegroundColor Yellow
    }
    elseif ($status -eq "running") {
        Write-Host "Stopping $instanceId..." -ForegroundColor Cyan

        aws ec2 stop-instances `
            --instance-ids $instanceId `
            --region $region

        if ($LASTEXITCODE -eq 0) {
            Write-Host "Stop request sent for $instanceId." -ForegroundColor Green
        }
        else {
            Write-Host "Failed to stop $instanceId." -ForegroundColor Red
        }
    }
    else {
        Write-Host "$instanceId is currently: $status" -ForegroundColor Yellow
        Write-Host "It may be transitioning. Run the script again later."
    }
}
