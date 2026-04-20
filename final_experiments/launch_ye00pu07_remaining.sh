#!/bin/bash
# ══════════════════════════════════════════════════════════════════════
# Launch remaining ye00pu07 runs on separate VMs.
# The main VM finished seg (no-overlap) + class for all 3 seeds.
# Still missing: overlap training (seed 123/456), threshold search, baseline.
# Seed 42 overlap is still running on the original VM.
#
# Usage:
#   bash final_experiments/launch_ye00pu07_remaining.sh setup   # upload code
#   bash final_experiments/launch_ye00pu07_remaining.sh launch  # create 3 VMs
#   bash final_experiments/launch_ye00pu07_remaining.sh status  # check progress
#   bash final_experiments/launch_ye00pu07_remaining.sh logs VM # tail VM log
# ══════════════════════════════════════════════════════════════════════
set -euo pipefail

PROJECT=$(gcloud config get-value project 2>/dev/null)
ZONES=(europe-west4-a europe-west4-b europe-west4-c)
MACHINE_TYPE="n1-standard-4"
BUCKET="gs://${PROJECT}-moove-final-exp"
RAW_DATA_BUCKET="gs://${PROJECT}-moove-raw-data"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

BIRD="ye00pu07"
BIRD_ZIP="bird_1"

CMD="${1:-help}"

# ══════════════════════════════════════════════════════════════════════
setup() {
    echo "=== Uploading repo (code only) ==="
    gsutil -m rm -r "${BUCKET}/repo/" 2>/dev/null || true
    gsutil -m rsync -r \
        -x "\.venv|.*\.pyc$|__pycache__|\.git|final_experiments/results|paper_experiments/results|docs/build|new_plots|copilot_recovery|.*\.pth$|.*\.pkl$|.*\.npz$|.*\.zip$|.*\.tar\.gz$" \
        "$REPO_DIR" "${BUCKET}/repo/"
    echo "Setup done."
}

# ══════════════════════════════════════════════════════════════════════
# Generate a startup script. $1 = VM label, $2 = training commands block
_make_startup_script() {
    local label="$1"
    local commands="$2"
    cat <<SCRIPT
#!/bin/bash
set -euo pipefail
export HOME="\${HOME:-/root}"
exec > /var/log/moove-training.log 2>&1

echo "=== VM: ${label} ==="
echo "Started: \$(date -u)"

BUCKET="${BUCKET}"
RAW_DATA_BUCKET="${RAW_DATA_BUCKET}"
BIRD="${BIRD}"
REPO_DIR="/opt/moove"
RAW_DATA_DIR="/opt/moove-raw"

# System deps
apt-get update -qq && apt-get install -y -qq unzip

export MPLBACKEND=Agg

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source "\$HOME/.cargo/env" 2>/dev/null || true
export PATH="\$HOME/.local/bin:\$PATH"

# Download code
mkdir -p "\$REPO_DIR"
gsutil -m rsync -r "\${BUCKET}/repo/" "\$REPO_DIR/"

# Download raw data
mkdir -p "\$RAW_DATA_DIR"
gsutil cp "\${RAW_DATA_BUCKET}/${BIRD_ZIP}.zip" /tmp/raw_data.zip
cd "\$RAW_DATA_DIR" && unzip /tmp/raw_data.zip && rm /tmp/raw_data.zip

export MOOVE_RAW_DATA_BASE="\$RAW_DATA_DIR"
cd "\$REPO_DIR"

# Install Python deps
echo "Installing Python dependencies..."
uv sync --no-dev
echo "Dependencies installed."

# Download existing results (needed for eval_only runs that load .pth models)
mkdir -p "final_experiments/results/${BIRD}"
gsutil -m rsync -r "\${BUCKET}/results/${BIRD}/" "final_experiments/results/${BIRD}/" || true

# ── Training commands ──
${commands}

# Upload results
gsutil -m rsync -r "final_experiments/results/${BIRD}/" "\${BUCKET}/results/${BIRD}/"

echo "Done: \$(date -u)"
shutdown -h now
SCRIPT
}

# ══════════════════════════════════════════════════════════════════════
launch() {
    local vms=(
        "moove-ye00pu07-overlap-123"
        "moove-ye00pu07-overlap-456"
        "moove-ye00pu07-rest"
    )

    # VM 1: overlap training seed 123 + its threshold search
    local cmd_overlap_123='
echo "=== Overlap training seed 123 ==="
uv run python3 final_experiments/train_seg.py --bird "$BIRD" --seed 123 --overlap_chunks

echo "=== Overlap threshold search seed 123 ==="
uv run python3 final_experiments/train_seg.py --bird "$BIRD" --seed 123 --eval_only --threshold_search --overlap_chunks
'

    # VM 2: overlap training seed 456 + its threshold search
    local cmd_overlap_456='
echo "=== Overlap training seed 456 ==="
uv run python3 final_experiments/train_seg.py --bird "$BIRD" --seed 456 --overlap_chunks

echo "=== Overlap threshold search seed 456 ==="
uv run python3 final_experiments/train_seg.py --bird "$BIRD" --seed 456 --eval_only --threshold_search --overlap_chunks
'

    # VM 3: no-overlap threshold search (3 seeds) + baseline (3 seeds)
    local cmd_rest='
echo "=== No-overlap threshold search ==="
for SEED in 42 123 456; do
    echo "--- Threshold search seed $SEED ---"
    uv run python3 final_experiments/train_seg.py --bird "$BIRD" --seed $SEED --eval_only --threshold_search
done

echo "=== Baseline ==="
uv run python3 final_experiments/run_all.py --bird "$BIRD" --type baseline
'

    local commands=("$cmd_overlap_123" "$cmd_overlap_456" "$cmd_rest")

    for i in 0 1 2; do
        local vm_name="${vms[$i]}"
        echo "=== Launching $vm_name ==="
        local tmpfile
        tmpfile=$(mktemp)
        _make_startup_script "$vm_name" "${commands[$i]}" > "$tmpfile"

        local launched=false
        for zone in "${ZONES[@]}"; do
            if gcloud compute instances create "$vm_name" \
                --zone="$zone" \
                --machine-type="$MACHINE_TYPE" \
                --image-family=debian-12 \
                --image-project=debian-cloud \
                --boot-disk-size=20GB \
                --metadata-from-file=startup-script="$tmpfile" \
                --scopes=storage-rw \
                --no-restart-on-failure \
                --maintenance-policy=TERMINATE 2>&1; then
                echo "  $vm_name launched in $zone."
                launched=true
                break
            else
                echo "  Zone $zone unavailable, trying next..."
            fi
        done
        rm -f "$tmpfile"
        if [ "$launched" = false ]; then
            echo "  FAILED: Could not launch $vm_name in any zone!"
        fi
    done

    echo ""
    echo "All VMs launched. Monitor with:"
    echo "  bash final_experiments/launch_ye00pu07_remaining.sh status"
}

# ══════════════════════════════════════════════════════════════════════
status() {
    local vms=(
        "moove-ye00pu07-overlap-123"
        "moove-ye00pu07-overlap-456"
        "moove-ye00pu07-rest"
        "moove-final-ye00pu07"
    )
    echo "=== VM Status ==="
    for vm_name in "${vms[@]}"; do
        local found=false
        for zone in "${ZONES[@]}"; do
            local s
            s=$(gcloud compute instances describe "$vm_name" --zone="$zone" \
                --format="value(status)" 2>/dev/null) && {
                echo "  $vm_name ($zone): $s"
                found=true
                break
            }
        done
        if [ "$found" = false ]; then
            echo "  $vm_name: NOT_FOUND"
        fi
    done
}

# ══════════════════════════════════════════════════════════════════════
logs() {
    local vm_name="${2:-}"
    if [ -z "$vm_name" ]; then
        echo "Usage: $0 logs VM_NAME"
        echo "Example: $0 logs moove-ye00pu07-overlap-123"
        exit 1
    fi
    for zone in "${ZONES[@]}"; do
        gcloud compute ssh "$vm_name" --zone="$zone" \
            --command="tail -50 /var/log/moove-training.log" 2>/dev/null && break
    done
}

# ══════════════════════════════════════════════════════════════════════
cleanup() {
    local vms=(
        "moove-ye00pu07-overlap-123"
        "moove-ye00pu07-overlap-456"
        "moove-ye00pu07-rest"
    )
    echo "=== Deleting remaining ye00pu07 VMs ==="
    for vm_name in "${vms[@]}"; do
        for zone in "${ZONES[@]}"; do
            gcloud compute instances delete "$vm_name" --zone="$zone" --quiet 2>/dev/null && {
                echo "  Deleted $vm_name ($zone)"
                break
            }
        done
    done
}

# ══════════════════════════════════════════════════════════════════════
case "$CMD" in
    setup)   setup ;;
    launch)  launch ;;
    status)  status ;;
    logs)    logs "$@" ;;
    cleanup) cleanup ;;
    *)
        echo "Usage: $0 {setup|launch|status|cleanup|logs}"
        echo "  setup   — upload latest code to GCS"
        echo "  launch  — create 3 VMs for remaining ye00pu07 runs"
        echo "  status  — check VM status (incl. original VM)"
        echo "  cleanup — delete the 3 VMs"
        echo "  logs VM — tail training log on a VM"
        ;;
esac
