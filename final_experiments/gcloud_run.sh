#!/bin/bash
# ══════════════════════════════════════════════════════════════════════
# GCloud Parallel Training — final_experiments
# One VM per bird (5 VMs), runs seg + class for 3 seeds each.
# Datasets are built on-the-fly from raw WAV data (no pre-built PKLs).
# VMs auto-shutdown after training; results are uploaded to GCS bucket.
#
# Usage:
#   gcloud auth login
#   gcloud config set project YOUR_PROJECT_ID
#   bash final_experiments/gcloud_run.sh setup    # upload code to GCS
#   bash final_experiments/gcloud_run.sh launch   # create 5 VMs
#   bash final_experiments/gcloud_run.sh status   # check progress
#   bash final_experiments/gcloud_run.sh collect  # download results
#   bash final_experiments/gcloud_run.sh cleanup  # delete VMs + bucket
# ══════════════════════════════════════════════════════════════════════
set -euo pipefail

PROJECT=$(gcloud config get-value project 2>/dev/null)
ZONE="europe-west4-a"
MACHINE_TYPE="n1-standard-4"       # 4 vCPU, 15 GB RAM
BUCKET="gs://${PROJECT}-moove-final-exp"
RAW_DATA_BUCKET="gs://${PROJECT}-moove-raw-data"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

BIRDS=(ye00pu07 bu04bk04 gy07bu07 br08pk08 ye04gr05)

# Bird name → ZIP name mapping
bird_to_zip() {
    case "$1" in
        ye00pu07) echo "bird_1" ;;
        bu04bk04) echo "bird_2" ;;
        gy07bu07) echo "bird_3" ;;
        br08pk08) echo "bird_4" ;;
        ye04gr05) echo "bird_5" ;;
        *) echo "unknown" ;;
    esac
}

CMD="${1:-help}"

# ══════════════════════════════════════════════════════════════════════
setup() {
    echo "=== Creating bucket ==="
    gsutil mb -l europe-west4 "$BUCKET" 2>/dev/null || true

    echo "=== Clearing old repo upload ==="
    gsutil -m rm -r "${BUCKET}/repo/" 2>/dev/null || true

    echo "=== Uploading repo (code only, no PKLs) ==="
    # Exclude venv, results, caches — VM installs deps itself via uv sync
    gsutil -m rsync -r \
        -x "\.venv|.*\.pyc$|__pycache__|\.git|final_experiments/results|paper_experiments/results" \
        "$REPO_DIR" "${BUCKET}/repo/"

    echo "Setup done. Bucket: $BUCKET"
    echo "Raw data bucket  : $RAW_DATA_BUCKET"
}

# ══════════════════════════════════════════════════════════════════════
_startup_script() {
    local bird="$1"
    local bird_zip
    bird_zip="$(bird_to_zip "$bird")"
    cat <<SCRIPT
#!/bin/bash
set -euo pipefail
exec > /var/log/moove-training.log 2>&1

BUCKET="${BUCKET}"
RAW_DATA_BUCKET="${RAW_DATA_BUCKET}"
BIRD="${bird}"
BIRD_ZIP="${bird_zip}"
REPO_DIR="/opt/moove"
RAW_DATA_DIR="/opt/moove-raw"

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source "\$HOME/.cargo/env" 2>/dev/null || true
export PATH="\$HOME/.local/bin:\$PATH"

# Download and extract code
mkdir -p "\$REPO_DIR"
gsutil -m rsync -r "\${BUCKET}/repo/" "\$REPO_DIR/"

# Download and extract raw training data for this bird
mkdir -p "\$RAW_DATA_DIR"
gsutil cp "\${RAW_DATA_BUCKET}/\${BIRD_ZIP}.zip" /tmp/raw_data.zip
cd "\$RAW_DATA_DIR" && unzip /tmp/raw_data.zip && rm /tmp/raw_data.zip

export MOOVE_RAW_DATA_BASE="\$RAW_DATA_DIR"

cd "\$REPO_DIR"

# Install deps
uv sync --no-dev 2>/dev/null || uv pip install -r requirements.txt 2>/dev/null || true

# Run training for this bird (3 seeds × seg + class)
uv run python3 final_experiments/run_all.py --bird "\$BIRD"

# Upload results
gsutil -m rsync -r "final_experiments/results/\$BIRD/" "\${BUCKET}/results/\$BIRD/"

echo "Training complete for \$BIRD"
# Auto-shutdown
shutdown -h now
SCRIPT
}

# ══════════════════════════════════════════════════════════════════════
launch() {
    for bird in "${BIRDS[@]}"; do
        local vm_name="moove-final-${bird//_/-}"
        echo "=== Launching $vm_name ==="
        local startup
        startup="$(_startup_script "$bird")"
        gcloud compute instances create "$vm_name" \
            --zone="$ZONE" \
            --machine-type="$MACHINE_TYPE" \
            --image-family=debian-12 \
            --image-project=debian-cloud \
            --boot-disk-size=20GB \
            --metadata=startup-script="$startup" \
            --scopes=storage-rw \
            --no-restart-on-failure \
            --maintenance-policy=TERMINATE
        echo "  VM $vm_name launched."
    done
    echo ""
    echo "All VMs launched. Monitor with: bash final_experiments/gcloud_run.sh status"
}

# ══════════════════════════════════════════════════════════════════════
status() {
    echo "=== VM Status ==="
    for bird in "${BIRDS[@]}"; do
        local vm_name="moove-final-${bird//_/-}"
        local s
        s=$(gcloud compute instances describe "$vm_name" --zone="$ZONE" \
            --format="value(status)" 2>/dev/null || echo "NOT_FOUND")
        echo "  $vm_name: $s"
    done

    echo ""
    echo "=== Results in bucket ==="
    gsutil ls "${BUCKET}/results/" 2>/dev/null || echo "  (no results yet)"
}

# ══════════════════════════════════════════════════════════════════════
collect() {
    local out_dir="$REPO_DIR/final_experiments/results"
    echo "=== Downloading results to $out_dir ==="
    gsutil -m rsync -r "${BUCKET}/results/" "$out_dir/"
    echo "Done."
}

# ══════════════════════════════════════════════════════════════════════
cleanup() {
    read -rp "Delete all VMs and bucket ${BUCKET}? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    for bird in "${BIRDS[@]}"; do
        local vm_name="moove-final-${bird//_/-}"
        gcloud compute instances delete "$vm_name" --zone="$ZONE" --quiet 2>/dev/null \
            && echo "  Deleted $vm_name" || echo "  $vm_name not found (already gone?)"
    done
    gsutil rm -r "$BUCKET" && echo "Deleted bucket $BUCKET"
}

# ══════════════════════════════════════════════════════════════════════
help() {
    grep '^#' "$0" | sed 's/^# \?//'
}

# ── Dispatch ─────────────────────────────────────────────────────────
case "$CMD" in
    setup)   setup   ;;
    launch)  launch  ;;
    status)  status  ;;
    collect) collect ;;
    cleanup) cleanup ;;
    *)       help    ;;
esac
