pipeline {
    agent any

    environment {
        DOCKER_IMAGE = 'gs-rest-service'
        DOCKER_TAG = "${BUILD_NUMBER}"
        SLACK_WEBHOOK_URL = 'https://hooks.slack.com/services/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'
        MAVEN_OPTS = '-Dmaven.repo.local=.m2/repository'
    }

    triggers {
        pollSCM('H/5 * * * *') // koristi webhook ako možeš, u suprotnom ovo
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    slackSend(":construction: Build #${BUILD_NUMBER} started on branch ${env.BRANCH_NAME}")
                }
                checkout scm

                script {
                    env.GIT_COMMIT_MSG = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()
                    env.GIT_AUTHOR = sh(script: 'git log -1 --pretty=%an', returnStdout: true).trim()
                }
            }
        }

        stage('Build & Test') {
            steps {
                dir('complete') {
                    sh 'mvn clean package -B'
                }
            }
            post {
                success {
                    script {
                        slackSend(":white_check_mark: Build and tests succeeded for build #${BUILD_NUMBER}")
                    }
                }
                failure {
                    script {
                        slackSend(":x: Build or tests failed for build #${BUILD_NUMBER}")
                    }
                    error("Build failed")
                }
            }
        }

        stage('Docker Build') {
            steps {
                dir('complete') {
                    script {
                        dockerImage = docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}")
                    }
                }
            }
        }

        stage('Docker Test') {
            steps {
                script {
                    sh """
                    docker stop gs-rest-service-test || true
                    docker rm gs-rest-service-test || true
                    docker run -d --name gs-rest-service-test -p 7777:777 ${DOCKER_IMAGE}:${DOCKER_TAG}
                    sleep 20
                    curl -f http://localhost:7777/greeting
                    docker stop gs-rest-service-test
                    docker rm gs-rest-service-test
                    """
                }
            }
        }

        stage('Deploy') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: '723ae88a-a5b9-4a29-9c79-a5bc81dd63f4',
                    usernameVariable: 'GIT_USERNAME',
                    passwordVariable: 'GIT_PASSWORD'
                )]) {
                    sh """
                    git config user.name "Jenkins CI"
                    git config user.email "jenkins@example.com"
                    git checkout ${env.BRANCH_NAME}
                    echo "Triggering redeploy from Jenkins at $(date)" > trigger.txt
                    git add trigger.txt
                    git commit -m "Jenkins triggered redeploy for build #${BUILD_NUMBER}" || echo "No changes to commit"
                    git push https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/urosorolicki/gs-rest-service.git ${env.BRANCH_NAME}
                    """

                    script {
                        slackSend(":rocket: GitHub push za deploy uspešan za build #${BUILD_NUMBER}")
                    }
                }
            }
        }
    }

    post {
        success {
            slackSend(":tada: Build #${BUILD_NUMBER} uspešno završen!\nAutor: ${env.GIT_AUTHOR}\nPoruka: ${env.GIT_COMMIT_MSG}")
        }
        failure {
            slackSend(":warning: Build #${BUILD_NUMBER} nije uspeo.\nAutor: ${env.GIT_AUTHOR}\nPoruka: ${env.GIT_COMMIT_MSG}")
        }
        always {
            cleanWs()
        }
    }
}

def slackSend(String message) {
    sh """
    curl -X POST -H 'Content-type: application/json' --data '{"text":"${message}"}' ${SLACK_WEBHOOK_URL}
    """
}
