
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        AWS_REGION     = 'ap-south-1'
        AWS_ACCOUNT_ID = '947317651355'
        ECR_REPOSITORY = 'cloudserve'
        APP_INSTANCE_ID = 'i-0e6a4b3f5d1f67638'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Validate Tools') {
            steps {
                sh '''
                    set -eu
                    /usr/local/bin/aws --version
                    git --version
                    docker --version
                    /usr/local/bin/aws sts get-caller-identity
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu
                    IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${GIT_COMMIT:-latest}"
                    docker build -t "$IMAGE_URI" ./app
                '''
            }
        }

        stage('Login and Push to ECR') {
            steps {
                sh '''
                    set -eu
                    REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    IMAGE_TAG="${GIT_COMMIT:-latest}"
                    IMAGE_URI="${REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"

                    /usr/local/bin/aws ecr get-login-password \
                      --region "$AWS_REGION" |
                      docker login --username AWS --password-stdin "$REGISTRY"

                    docker push "$IMAGE_URI"
                '''
            }
        }

        stage('Deploy through SSM') {
            steps {
                sh '''
                    set -eu
                    echo "Preparing deployment to ${APP_INSTANCE_ID}"

                    /usr/local/bin/aws ssm send-command \
                      --region "$AWS_REGION" \
                      --instance-ids "$APP_INSTANCE_ID" \
                      --document-name "AWS-RunShellScript" \
                      --comment "CloudServe Jenkins deployment ${BUILD_NUMBER}" \
                      --parameters commands="echo Jenkins deployment target verified"
                '''
            }
        }
    }

    post {
        success {
            echo 'CloudServe Jenkins pipeline completed.'
        }
        failure {
            echo 'Pipeline failed. Review the stage logs before retrying.'
        }
        always {
            sh 'docker logout "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com" || true'
        }
    }
}
