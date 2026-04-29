#!/bin/bash
#
# Academic Achievement Summarizer - Update Script
# UNMC Department of Anesthesiology
#
# Run this on the production server every time you pull new code from GitHub.
# It performs the full update sequence and verifies the result, so you cannot
# accidentally forget collectstatic (which causes the "no styling" symptom).
#
# Usage:
#   cd /opt/academic-achievement
#   ./update.sh
#
# Safe to run when no update is needed -- it will detect that and still
# refresh static files / restart the service.

set -euo pipefail

APP_NAME="academic-achievement"
APP_DIR="/opt/${APP_NAME}"
SERVICE_NAME="${APP_NAME}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Allow running from anywhere -- always operate inside APP_DIR.
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR"
fi

if [ ! -f manage.py ]; then
    echo -e "${RED}ERROR: manage.py not found.${NC} Run this script from ${APP_DIR}." >&2
    exit 1
fi

if [ ! -d venv ]; then
    echo -e "${RED}ERROR: virtualenv not found at ${APP_DIR}/venv.${NC}" >&2
    echo "Run the initial deploy.sh first." >&2
    exit 1
fi

echo "========================================"
echo " Academic Achievement Summarizer"
echo " Update from GitHub"
echo "========================================"

OLD_COMMIT=$(git rev-parse --short HEAD)

echo ""
echo -e "${YELLOW}[1/6] Pulling latest code from GitHub...${NC}"
git fetch --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse '@{u}')
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "  Already up to date (no new commits)."
else
    git pull --ff-only
fi
NEW_COMMIT=$(git rev-parse --short HEAD)

echo ""
echo -e "${YELLOW}[2/6] Activating virtualenv...${NC}"
# shellcheck disable=SC1091
source venv/bin/activate

echo ""
echo -e "${YELLOW}[3/6] Installing/updating Python dependencies...${NC}"
pip install -r requirements.txt --quiet --disable-pip-version-check

echo ""
echo -e "${YELLOW}[4/6] Running database migrations...${NC}"
python manage.py migrate --noinput

echo ""
echo -e "${YELLOW}[5/6] Collecting static files (CSS, JS, images)...${NC}"
python manage.py collectstatic --noinput

echo ""
echo -e "${YELLOW}[6/6] Restarting service...${NC}"
sudo systemctl restart "$SERVICE_NAME"
sleep 2

# Verify service came back up.
if ! sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${RED}FAILED${NC} - service did not start. Last log lines:" >&2
    sudo journalctl -u "$SERVICE_NAME" -n 30 --no-pager >&2
    exit 1
fi

# Verify static files are in place. This catches the "deployed site has no
# styling" bug -- if collectstatic silently failed or got skipped, the
# staticfiles/ tree will be missing or nearly empty.
STATIC_COUNT=$(find staticfiles -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$STATIC_COUNT" -lt 10 ]; then
    echo -e "${RED}WARNING${NC}: only ${STATIC_COUNT} files in staticfiles/ -- the site will render with no styling." >&2
    echo "Re-run: python manage.py collectstatic --noinput --clear" >&2
    exit 1
fi

VERSION=$(cat VERSION 2>/dev/null || echo "unknown")

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN} Update complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo "  Version:      ${VERSION}"
if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    echo "  Commit:       ${NEW_COMMIT} (no change)"
else
    echo "  Commit:       ${OLD_COMMIT} -> ${NEW_COMMIT}"
fi
echo "  Static files: ${STATIC_COUNT}"
echo "  Service:      running"
echo ""
echo "Verify in a browser: hard-refresh the site (Cmd/Ctrl+Shift+R)."
