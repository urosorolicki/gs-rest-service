pipeline {
    agent any

    environment {
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-creds') // ID tvojih Docker Hub kredencijala u Jenkinsu
        SLACK_WEBHOOK = "https://hooks.slack.com/services/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"
        IMAGE_NAME = "urosorolicki/gs-rest-service"
        IMAGE_TAG = "latest"
    }

    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/urosorolicki/gs-rest-service'
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
                    docker.withRegistry('https://index.docker.io/v1/', 'dockerhub-creds') {
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
            curl -X POST -H 'Content-type: application/json' --data '{"text":":white_check_mark: Build i Docker push uspešni!"}' ${SLACK_WEBHOOK}
            """
        }
        failure {
            sh """
            curl -X POST -H 'Content-type: application/json' --data '{"text":":x: Build ili Docker push nisu uspeli."}' ${SLACK_WEBHOOK}
            """
        }
    }
}
