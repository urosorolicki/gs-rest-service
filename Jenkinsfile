pipeline {
    agent any

    environment {
        SLACK_WEBHOOK = 'https://hooks.slack.com/services/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'
        IMAGE_NAME = 'gs-rest-service'
        CONTAINER_PORT = '7777'
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

        stage('Docker Build') {
            steps {
                sh """
                docker build -t ${IMAGE_NAME} ./complete
                """
            }
        }

        stage('Docker Run Test') {
            steps {
                script {
                    sh """
                    docker run -d --name test_container -p ${CONTAINER_PORT}:${CONTAINER_PORT} ${IMAGE_NAME}
                    sleep 10
                    curl -f http://localhost:${CONTAINER_PORT}/greeting || (echo "App not responding" && exit 1)
                    docker stop test_container
                    docker rm test_container
