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
                    sh 'chmod +x ./mvnw'
                    sh './mvnw clean package -DskipTests'
                }
            }
        }

        stage('Docker Version Check') {
            steps {
                sh 'docker version'
            }
        }

        stage('Docker Build & Push') {
            steps {
                script {
                    // Login to Docker Hub
                    sh """
                       echo "${DOCKERHUB_CREDENTIALS_PSW}" | docker login -u "${DOCKERHUB_CREDENTIALS_USR}" --password-stdin
                    """

                    // Build image
                    sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ./complete"

                    // Push image
                    sh "docker push ${IMAGE_NAME}:${IMAGE_TAG}"

                    // Logout just to be clean
                    sh "docker logout"
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
