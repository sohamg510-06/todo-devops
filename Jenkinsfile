pipeline {
    agent any

    environment {
        DOCKERHUB_USER  = '05ace'
        IMAGE           = "${DOCKERHUB_USER}/todo-devops"
        DOCKERHUB_CREDS = credentials('dockerhub-creds')
    }

    options {
        disableConcurrentBuilds()
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
            }
        }

        stage('Build') {
            steps {
                sh '. venv/bin/activate && python -m py_compile app.py'
            }
        }

        stage('Test') {
            steps {
                sh '. venv/bin/activate && pytest -v'
            }
        }

        stage('Docker Build') {
            steps {
                sh "docker build -t ${IMAGE}:${BUILD_NUMBER} -t ${IMAGE}:latest ."
            }
        }

        stage('Docker Push') {
            steps {
                sh 'echo $DOCKERHUB_CREDS_PSW | docker login -u $DOCKERHUB_CREDS_USR --password-stdin'
                sh "docker push ${IMAGE}:${BUILD_NUMBER}"
                sh "docker push ${IMAGE}:latest"
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker rm -f todo-app || true'
                sh "docker run -d --name todo-app --network devops-net -p 5000:5000 -v todo-data:/data ${IMAGE}:latest"
            }
        }
    }

    post {
        success { echo 'Pipeline SUCCESS - app deployed at http://localhost:5000' }
        failure { echo 'Pipeline FAILED - deployment skipped' }
    }
}
