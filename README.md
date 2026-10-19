# To-Do DevOps Mini-Project

Flask To-Do app with a full DevOps pipeline:
GitHub -> Jenkins -> Test (pytest) -> Docker build -> Docker Hub -> Deploy -> Prometheus -> Grafana -> Alerts

## Run order (one night guide)

### 1. Test the app locally
    python -m venv venv
    venv\Scripts\activate        (Windows)   |   source venv/bin/activate   (Linux/Mac)
    pip install -r requirements.txt
    pytest -v
    python app.py                -> http://localhost:5000   (Ctrl+C to stop)

### 2. Push to GitHub
Create an empty public repo `todo-devops` on GitHub, then:
    git init
    git add .
    git commit -m "Initial application"
    git branch -M main
    git remote add origin https://github.com/<your-username>/todo-devops.git
    git push -u origin main

### 3. Start monitoring stack (also creates the devops-net network)
    docker compose up -d
    Prometheus -> http://localhost:9090
    Grafana    -> http://localhost:3000   (admin / admin)

### 4. Start Jenkins
    docker build -t jenkins-docker ./jenkins
    docker run -d --name jenkins -u root -p 8080:8080 -p 50000:50000 -v jenkins_home:/var/jenkins_home -v /var/run/docker.sock:/var/run/docker.sock jenkins-docker
    docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
Open http://localhost:8080, paste password, install suggested plugins, create admin user.

### 5. Jenkins setup
- Manage Jenkins > Credentials > Global > Add Credentials: Username with password
  (Docker Hub username + access token), ID = `dockerhub-creds`
- Edit `Jenkinsfile`: replace YOUR_DOCKERHUB_USERNAME, commit and push
- New Item > Pipeline > Pipeline script from SCM > Git > repo URL > Branch `*/main` > Script Path `Jenkinsfile`
- Click Build Now once (afterwards it auto-triggers on every push via Poll SCM)

### 6. Grafana dashboard
- Data source Prometheus is already added
- Dashboards > New > Import > ID `1860` > Load > select Prometheus > Import (CPU, memory, disk, network)
- Add one panel with query: `rate(flask_http_request_total[1m])` (app requests)
- Open the app and click around to generate requests

### 7. Trigger alerts (Prometheus -> Alerts, http://localhost:9090/alerts)
- App down:   `docker stop todo-app`   (wait ~1 min -> AppDown FIRING)  then `docker start todo-app`
- CPU > 80%:  `docker run --rm alpine sh -c 'for i in $(seq $(nproc)); do (while :; do :; done) & done; sleep 180'`

### 8. Final demo
1. Edit the heading in templates/index.html
2. git add . ; git commit -m "Update heading" ; git push
3. Jenkins auto-starts -> Checkout, Install, Build, Test, Docker Build, Push, Deploy all green
4. Refresh http://localhost:5000 and show the change
5. Show Grafana dashboard, then trigger the alert
6. Viva: break a test in test_app.py, push, show the pipeline stopping at Test (no deploy)
