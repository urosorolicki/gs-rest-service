pipeline {
    agent any
    
    environment {
        DOCKER_IMAGE = 'gs-rest-service'
        DOCKER_TAG = "${BUILD_NUMBER}"
        SLACK_CHANNEL_CI = '#gs-rest-service-ci'
        MAVEN_OPTS = '-Dmaven.repo.local=.m2/repository'
    }
    
    tools {
        maven 'Maven-3.9.6'
        jdk 'OpenJDK-17'
    }
    
    triggers {
        // Poll SCM every 5 minutes for changes on master and develop branches
        pollSCM('H/5 * * * *')
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    // Send build start notification
                    slackSend(
                        channel: env.SLACK_CHANNEL_CI,
                        color: 'warning',
                        message: ":construction: Build #${BUILD_NUMBER} started for ${env.BRANCH_NAME} branch\n" +
                                "Commit: ${env.GIT_COMMIT}\n" +
                                "Job: ${env.JOB_NAME}"
                    )
                }
                
                checkout scm
                
                script {
                    // Get commit info for notifications
                    env.GIT_COMMIT_MSG = sh(
                        script: 'git log -1 --pretty=%B',
                        returnStdout: true
                    ).trim()
                    env.GIT_AUTHOR = sh(
                        script: 'git log -1 --pretty=%an',
                        returnStdout: true
                    ).trim()
                }
            }
        }
        
        stage('Build') {
            steps {
                dir('complete') {
                    sh 'mvn clean compile -B'
                }
            }
        }
        
        stage('Test') {
            steps {
                dir('complete') {
                    script {
                        slackSend(
                            channel: env.SLACK_CHANNEL_CI,
                            color: 'good',
                            message: ":test_tube: Running tests for build #${BUILD_NUMBER}"
                        )
                    }
                    
                    sh 'mvn test -B'
                }
            }
            post {
                always {
                    dir('complete') {
                        // Publish test results
                        publishTestResults testResultsPattern: 'target/surefire-reports/*.xml'
                        
                        script {
                            // Read test results
                            def testResults = currentBuild.testResultAction
                            def testSummary = ""
                            
                            if (testResults) {
                                testSummary = """
:test_tube: *Test Results for Build #${BUILD_NUMBER}*
• Total Tests: ${testResults.totalCount}
• Passed: ${testResults.totalCount - testResults.failCount - testResults.skipCount}
• Failed: ${testResults.failCount}
• Skipped: ${testResults.skipCount}
"""
                                
                                def color = testResults.failCount > 0 ? 'danger' : 'good'
                                
                                slackSend(
                                    channel: env.SLACK_CHANNEL_CI,
                                    color: color,
                                    message: testSummary
                                )
                            }
                        }
                    }
                }
            }
        }
        
        stage('Package') {
            steps {
                dir('complete') {
                    sh 'mvn package -DskipTests -B'
                }
            }
            post {
                success {
                    dir('complete') {
                        archiveArtifacts artifacts: 'target/*.jar', allowEmptyArchive: false
                    }
                }
            }
        }
        
        stage('Docker Build') {
            when {
                anyOf {
                    branch 'master'
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                dir('complete') {
                    script {
                        // Build Docker image
                        def image = docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}")
                        
                        // Tag as latest for main/master branch
                        if (env.BRANCH_NAME == 'main' || env.BRANCH_NAME == 'master') {
                            sh "docker tag ${DOCKER_IMAGE}:${DOCKER_TAG} ${DOCKER_IMAGE}:latest"
                        }
                        
                        // Store image info for deployment stage
                        env.DOCKER_IMAGE_FULL = "${DOCKER_IMAGE}:${DOCKER_TAG}"
                    }
                }
            }
        }
        
        stage('Docker Test') {
            when {
                anyOf {
                    branch 'master'
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    // Test the Docker container
                    sh """
                        # Stop any existing test container
                        docker stop gs-rest-service-test || true
                        docker rm gs-rest-service-test || true
                        
                        # Run container for testing
                        docker run -d --name gs-rest-service-test -p 7777:777 ${env.DOCKER_IMAGE_FULL}
                        
                        # Wait for service to start
                        sleep 30
                        
                        # Test the endpoint
                        curl -f http://localhost:7777/greeting || exit 1
                        
                        # Cleanup
                        docker stop gs-rest-service-test
                        docker rm gs-rest-service-test
                    """
                }
            }
        }
        
        stage('Trigger Deployment') {
            when {
                anyOf {
                    branch 'master'
                    branch 'main'
                }
            }
            steps {
                script {
                    // Trigger deployment job
                    build job: 'gs-rest-service-deploy', 
                          parameters: [
                              string(name: 'DOCKER_IMAGE', value: env.DOCKER_IMAGE_FULL),
                              string(name: 'BUILD_NUMBER', value: env.BUILD_NUMBER)
                          ],
                          wait: false
                }
            }
        }
    }
    
    post {
        success {
            slackSend(
                channel: env.SLACK_CHANNEL_CI,
                color: 'good',
                message: ":white_check_mark: Build #${BUILD_NUMBER} completed successfully!\n" +
                        "Branch: ${env.BRANCH_NAME}\n" +
                        "Author: ${env.GIT_AUTHOR}\n" +
                        "Commit: ${env.GIT_COMMIT_MSG}"
            )
        }
        
        failure {
            slackSend(
                channel: env.SLACK_CHANNEL_CI,
                color: 'danger',
                message: ":x: Build #${BUILD_NUMBER} failed!\n" +
                        "Branch: ${env.BRANCH_NAME}\n" +
                        "Author: ${env.GIT_AUTHOR}\n" +
                        "Commit: ${env.GIT_COMMIT_MSG}\n" +
                        "Check: ${env.BUILD_URL}"
            )
        }
        
        always {
            // Clean workspace
            cleanWs()
        }
    }
}
