#!/bin/bash
# Auto-update pi-display from GitHub
# Called by systemd timer — checks for new commits, pulls, and restarts service

main() {
    set -e

    DIR="$(cd "$(dirname "$0")" && pwd)"
    cd "$DIR"

    # Must be a git repo with a remote
    git rev-parse --git-dir >/dev/null 2>&1 || exit 0
    git remote get-url origin >/dev/null 2>&1 || exit 0

    # Fetch latest commits
    if ! git fetch origin --quiet 2>&1; then
        logger -t pi-display-updater "git fetch failed"
        exit 1
    fi

    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main 2>/dev/null) || exit 0

    [ "$LOCAL" = "$REMOTE" ] && exit 0

    # New commits available — protect config.json and pull
    [ -f config.json ] && cp -p config.json .config.json.bak

    git reset --hard "$REMOTE" --quiet

    # Restore config.json (not tracked, but be safe)
    [ -f .config.json.bak ] && mv .config.json.bak config.json

    # Restart the display service (use sudo since we run as non-root)
    sudo systemctl restart pi-display.service 2>/dev/null || true

    logger -t pi-display-updater "Updated from ${LOCAL:0:7} to ${REMOTE:0:7}, service restarted"
}

main "$@"
