
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    environment {
        AWS_REGION      = 'ap-south-1'
        AWS_ACCOUNT_ID  = '947317651355'
        ECR_REPOSITORY  = 'cloudserve'
        APP_INSTANCE_ID = 'i-0e6a4b3f5d1f67638'
        AWS_CLI         = '/usr/local/bin/aws'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.COMMIT_SHA = sh(
                        script: 'git rev-parse HEAD',
                        returnStdout: true
                    ).trim()
                    env.IMAGE_URI =
                        "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com/${env.ECR_REPOSITORY}:${env.COMMIT_SHA}"
                    env.REGISTRY =
                        "${env.AWS_ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
                    env.DEPLOY_SCRIPT_URL =
                        "https://raw.githubusercontent.com/omkrve/cloudserve2/${env.COMMIT_SHA}/scripts/deploy-on-ec2.sh"
                }
                echo 'Checked out CloudServe commit.'
            }
        }

        stage('Validate Tools and AWS Identity') {
            steps {
                sh '''
                    set -eu
                    "$AWS_CLI" --version
                    git --version
                    docker --version
                    python3 --version
                    curl --version
                    "$AWS_CLI" sts get-caller-identity
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu
                    docker build -t "$IMAGE_URI" ./app
                '''
            }
        }

        stage('Push Image to ECR') {
            steps {
                sh '''
                    set -eu
                    "$AWS_CLI" ecr get-login-password \
                      --region "$AWS_REGION" |
                      docker login \
                        --username AWS \
                        --password-stdin "$REGISTRY"

                    docker push "$IMAGE_URI"
                '''
            }
        }

        stage('Prepare Deployment') {
            steps {
                sh '''
                    set -eu

                    curl --fail --silent --show-error --location \
                      "$DEPLOY_SCRIPT_URL" \
                      -o downloaded-deploy-script.sh

                    cmp scripts/deploy-on-ec2.sh downloaded-deploy-script.sh

                    export IMAGE_URI DEPLOY_SCRIPT_URL AWS_REGION REGISTRY

                    python3 - <<'PY'
import json
import os

region = os.environ["AWS_REGION"]
registry = os.environ["REGISTRY"]
image = os.environ["IMAGE_URI"]
script_url = os.environ["DEPLOY_SCRIPT_URL"]

commands = [
    "set -eu",
    "aws ecr get-login-password --region " + region
        + " | docker login --username AWS --password-stdin " + registry,
    "curl --fail --silent --show-error --location "
        + script_url + " -o /tmp/cloudserve-deploy.sh",
    "chmod 700 /tmp/cloudserve-deploy.sh",
    "bash /tmp/cloudserve-deploy.sh " + image,
    "rm -f /tmp/cloudserve-deploy.sh"
]

with open("deployment-parameters.json", "w") as f:
    json.dump({"commands": commands}, f)
PY

                    "$AWS_CLI" sts get-caller-identity >/dev/null
                    echo "Prepared deployment for commit $COMMIT_SHA"
                '''
            }
        }

        stage('Deploy through SSM') {
            steps {
                script {
                    def commandId = sh(
                        script: '''
                            set -eu
                            "$AWS_CLI" ssm send-command \
                              --region "$AWS_REGION" \
                              --instance-ids "$APP_INSTANCE_ID" \
                              --document-name AWS-RunShellScript \
                              --comment "CloudServe Jenkins build ${BUILD_NUMBER}, commit ${COMMIT_SHA}" \
                              --parameters file://deployment-parameters.json \
                              --query 'Command.CommandId' \
                              --output text
                        ''',
                        returnStdout: true
                    ).trim()

                    echo "SSM command submitted: ${commandId}"

                    timeout(time: 7, unit: 'MINUTES') {
                        waitUntil {
                            def status = sh(
                                script: """
                                    "$AWS_CLI" ssm list-command-invocations \
                                      --region "$AWS_REGION" \
                                      --command-id '${commandId}' \
                                      --query 'CommandInvocations[0].Status' \
                                      --output text 2>/dev/null || true
                                """,
                                returnStdout: true
                            ).trim()

                            echo "Deployment status: ${status}"

                            if (status == 'Success') {
                                return true
                            }

                            if (['Failed', 'TimedOut', 'Cancelled',
                                 'Cancelling'].contains(status)) {
                                sh """
                                    "$AWS_CLI" ssm get-command-invocation \
                                      --region "$AWS_REGION" \
                                      --command-id '${commandId}' \
                                      --instance-id "$APP_INSTANCE_ID" \
                                      --query '{Status:Status,Output:StandardOutputContent,Error:StandardErrorContent}' \
                                      --output json || true
                                """
                                error("CloudServe deployment failed: ${status}")
                            }

                            sleep(time: 10, unit: 'SECONDS')
                            return false
                        }
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'CloudServe deployment completed successfully.'
        }
        failure {
            echo 'Pipeline failed. Review the stage logs and SSM output.'
        }
        always {
            sh '''
                rm -f deployment-parameters.json downloaded-deploy-script.sh
                docker logout "${REGISTRY:-947317651355.dkr.ecr.ap-south-1.amazonaws.com}" || true
            '''
        }
    }
}
