pipeline {
    agent any
    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-token-id')
        SLACK_WEBHOOK = credentials('SLACK_WEBHOOK')
        IMAGE_NAME = "orolickiuros/gs-rest-service"
        IMAGE_TAG = "latest"
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/urosorolicki/gs-rest-service'
            }
        }
        stage('Build') {
            steps {
                dir('complete') {
                    bat 'mvnw.cmd clean package -DskipTests'
                }
            }
        }
        stage('Docker Build & Push') {
            steps {
                script {
                    bat """
                        echo %DOCKERHUB_CREDENTIALS_PSW% | docker login -u %DOCKERHUB_CREDENTIALS_USR% --password-stdin
                        docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ./complete
                        docker push ${IMAGE_NAME}:${IMAGE_TAG}
                        docker logout
                    """
                }
            }
        }
    }
    post {
        success {
            bat """
            curl -X POST -H "Content-type: application/json" --data "{\\"text\\":\\"Build i Docker push uspešni!\\"}" %SLACK_WEBHOOK%
            """
        }
        failure {
            bat """
            curl -X POST -H "Content-type: application/json" --data "{\\"text\\":\\"Build ili Docker push nisu uspeli.\\"}" %SLACK_WEBHOOK%
            """
        }
    }
}
