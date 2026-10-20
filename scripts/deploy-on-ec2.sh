
#!/bin/bash
set -Eeuo pipefail

IMAGE_URI="${1:?Usage: deploy-on-ec2.sh IMAGE_URI}"

ENV_FILE="/run/cloudserve.env"
DATA_DIR="/var/lib/cloudserve/data"
UPLOAD_DIR="/var/lib/cloudserve/uploads"
CANDIDATE="cloudserve-candidate"
PREVIOUS="cloudserve-previous-$(date +%s)"
HAD_OLD=false

cleanup() {
  rm -f "$ENV_FILE"
}
trap cleanup EXIT

# Retrieve application settings from AWS Systems Manager Parameter Store.
SECRET_KEY=$(aws ssm get-parameter \
  --name "/cloudserve/dev/secret-key" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text)

ADMIN_USERNAME=$(aws ssm get-parameter \
  --name "/cloudserve/dev/admin-username" \
  --query "Parameter.Value" \
  --output text)

ADMIN_EMAIL=$(aws ssm get-parameter \
  --name "/cloudserve/dev/admin-email" \
  --query "Parameter.Value" \
  --output text)

ADMIN_PASSWORD=$(aws ssm get-parameter \
  --name "/cloudserve/dev/admin-password" \
  --with-decryption \
  --query "Parameter.Value" \
  --output text)

test -n "$SECRET_KEY"
test -n "$ADMIN_USERNAME"
test -n "$ADMIN_EMAIL"
test -n "$ADMIN_PASSWORD"

umask 077
printf 'SECRET_KEY=%s\nADMIN_USERNAME=%s\nADMIN_EMAIL=%s\nADMIN_PASSWORD=%s\nCLOUDSERVE_DATA_DIR=%s\nCLOUDSERVE_UPLOAD_DIR=%s\nCOOKIE_SECURE=false\n' \
  "$SECRET_KEY" "$ADMIN_USERNAME" "$ADMIN_EMAIL" "$ADMIN_PASSWORD" \
  "$DATA_DIR" "$UPLOAD_DIR" > "$ENV_FILE"
chmod 600 "$ENV_FILE"
unset SECRET_KEY ADMIN_USERNAME ADMIN_EMAIL ADMIN_PASSWORD

mkdir -p "$DATA_DIR" "$UPLOAD_DIR"
chown -R 1000:1000 /var/lib/cloudserve
chmod 750 /var/lib/cloudserve "$DATA_DIR" "$UPLOAD_DIR"

docker pull "$IMAGE_URI"
docker rm -f "$CANDIDATE" >/dev/null 2>&1 || true

# Test the new image before replacing the running application.
docker run -d \
  --name "$CANDIDATE" \
  --restart no \
  -p 127.0.0.1:5001:5000 \
  --env-file "$ENV_FILE" \
  -v "$DATA_DIR:/var/lib/cloudserve/data" \
  -v "$UPLOAD_DIR:/var/lib/cloudserve/uploads" \
  "$IMAGE_URI"

HEALTHY=false
for i in $(seq 1 12); do
  if curl -fsS http://127.0.0.1:5001/health >/dev/null; then
    HEALTHY=true
    break
  fi
  sleep 5
done

if [ "$HEALTHY" != true ]; then
  docker logs "$CANDIDATE" || true
  docker rm -f "$CANDIDATE" || true
  echo "Candidate health check failed; existing service was not replaced."
  exit 1
fi

docker rm -f "$CANDIDATE"

# Keep the previous container for rollback.
if docker inspect cloudserve >/dev/null 2>&1; then
  HAD_OLD=true
  docker stop cloudserve
  docker rename cloudserve "$PREVIOUS"
  docker update --restart=no "$PREVIOUS"
fi

rollback() {
  docker rm -f cloudserve >/dev/null 2>&1 || true
  if [ "$HAD_OLD" = true ]; then
    docker rename "$PREVIOUS" cloudserve
    docker start cloudserve
  fi
}

if ! docker run -d \
  --restart unless-stopped \
  --name cloudserve \
  -p 127.0.0.1:5000:5000 \
  --env-file "$ENV_FILE" \
  -v "$DATA_DIR:/var/lib/cloudserve/data" \
  -v "$UPLOAD_DIR:/var/lib/cloudserve/uploads" \
  "$IMAGE_URI"; then
  rollback
  exit 1
fi

HEALTHY=false
for i in $(seq 1 12); do
  if curl -fsS http://127.0.0.1:5000/health >/dev/null; then
    HEALTHY=true
    break
  fi
  sleep 5
done

if [ "$HEALTHY" != true ]; then
  docker logs cloudserve || true
  rollback
  echo "New service health check failed; rollback attempted."
  exit 1
fi

echo "CloudServe deployment succeeded."
