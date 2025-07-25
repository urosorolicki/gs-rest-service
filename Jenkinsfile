pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-token-id')
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
                    sh './mvnw clean package -DskipTests'
                }
            }
        }

        stage('Docker Build & Push') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-token-id') {
                        def appImage = docker.build("${IMAGE_NAME}:${IMAGE_TAG}", './complete')
                        appImage.push()
                    }
                }
            }
        }
    }

    post {
        success {
            sh """
            curl -X POST -H 'Content-type: application/json' --data '{"text":":white_check_mark: Build i Docker push uspešni!"}' ${env.SLACK_WEBHOOK}
            """
        }
        failure {
            sh """
            curl -X POST -H 'Content-type: application/json' --data '{"text":":x: Build ili Docker push nisu uspeli."}' ${env.SLACK_WEBHOOK}
            """
        }
    }
}
