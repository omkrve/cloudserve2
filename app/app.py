
from flask import Flask, render_template_string
from datetime import datetime, timezone
import os
import socket

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CloudServe | Infrastructure Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
        rel="stylesheet">
  <style>
    body { background: #f4f7fb; color: #172b4d; }
    .navbar { background: #102a43; }
    .hero { background: linear-gradient(120deg,#102a43,#176b87);
            color: white; border-radius: 18px; }
    .metric { border: 0; border-radius: 14px;
              box-shadow: 0 4px 16px #102a4310; }
    .dot { display:inline-block; width:9px; height:9px;
           border-radius:50%; background:#22c55e; }
  </style>
</head>
<body>
<nav class="navbar navbar-dark px-4 py-3">
  <span class="navbar-brand fw-bold">☁ CloudServe</span>
  <span class="text-light small">Infrastructure Operations</span>
</nav>

<main class="container py-5">
  <section class="hero p-4 p-md-5 mb-4">
    <p class="text-uppercase small mb-2">Cloud operations platform</p>
    <h1 class="fw-bold">Infrastructure at a glance.</h1>
    <p class="mb-0">A centralized view of your CloudServe environment.</p>
  </section>

  <div class="row g-3 mb-4">
    <div class="col-md-4">
      <div class="card metric p-4 h-100">
        <p class="text-secondary mb-2">Application status</p>
        <h3><span class="dot"></span> Operational</h3>
        <small class="text-secondary">Flask application is responding</small>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card metric p-4 h-100">
        <p class="text-secondary mb-2">Environment</p>
        <h3>{{ environment }}</h3>
        <small class="text-secondary">Deployment configuration</small>
      </div>
    </div>
    <div class="col-md-4">
      <div class="card metric p-4 h-100">
        <p class="text-secondary mb-2">Compute host</p>
        <h3>{{ hostname }}</h3>
        <small class="text-secondary">Current application container/host</small>
      </div>
    </div>
  </div>

  <div class="card metric p-4">
    <h5>System information</h5>
    <p class="mb-2">Current UTC time: {{ current_time }}</p>
    <p class="mb-2">Service: CloudServe Web</p>
    <p class="mb-0">Monitoring: AWS CloudWatch configuration planned</p>
  </div>
  <p class="text-secondary small mt-4">
    CloudServe demonstration dashboard · Infrastructure managed with Terraform
  </p>
</main>
</body>
</html>
"""

@app.get("/")
def dashboard():
    return render_template_string(
        HTML,
        environment=os.getenv("APP_ENV", "development"),
        hostname=socket.gethostname(),
        current_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

@app.get("/health")
def health():
    return {"status": "healthy", "service": "cloudserve"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
