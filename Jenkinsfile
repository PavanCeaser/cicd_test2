pipeline {
    agent any
    environment {
        DOCKER_HUB_REPO = 'devpavanhl/cicd_test'  // Lowercase repository name
        DOCKER_HUB_USERNAME = 'devpavanhl'
        DOCKER_HUB_PASSWORD = 'pa__    '
    }
    stages {
        stage('Clone Repository') {
            steps {
                git branch: 'main', url: 'https://github.com/PavanCeaser/cicd_test.git'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                   
                    bat 'docker build -t %DOCKER_HUB_REPO%:latest .'
                }
            }
        }
        stage('Push Docker Image') {
            steps {
                script {
                    
                    bat """
                        docker login -u %DOCKER_HUB_USERNAME% -p %DOCKER_HUB_PASSWORD%
                        docker push %DOCKER_HUB_REPO%:latest
                    """
                }
            }
        }
    }
    post {
        success {
            echo "Pipeline executed successfully!"
        }
        failure {
            echo "Pipeline failed. Please check the logs."
        }
    }
}
