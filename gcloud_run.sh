#!/bin/bash
set -o pipefail

# ══════════════════════════════════════════════════════════════════════
# GCloud Parallel Training — 5 VMs (one per bird) + 1 energy baseline
# VMs auto-deprovision, bucket stays for re-runs.
# ══════════════════════════════════════════════════════════════════════
# Usage:
#   1. gcloud auth login
#   2. gcloud config set project YOUR_PROJECT_ID
#   3. bash gcloud_run.sh setup    # upload code + PKLs + WAVs to GCS
#   4. bash gcloud_run.sh launch   # create 6 VMs (5 training + 1 baseline)
#   5. bash gcloud_run.sh status   # check progress
#   6. bash gcloud_run.sh collect  # download results when done
#   7. bash gcloud_run.sh cleanup  # delete VMs + bucket (interactive)
# ══════════════════════════════════════════════════════════════════════

PROJECT=$(gcloud config get-value project 2>/dev/null)
ZONE="europe-west4-a"
MACHINE_TYPE="e2-standard-4"        # 4 vCPU, 16GB RAM — plenty for small Conv1D
BUCKET="gs://${PROJECT}-moove-training"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TRAINING_DATA_DIR="$HOME/.moove/training_data"
REC_DATA_DIR="$HOME/.moove/rec_data"

# Bird config — parallel arrays (bash 3.x compatible)
BIRDS="ye00pu07 bu04bk04 gy07bu07 br08pk08 ye04gr05"
SEG_PKLS="bird1_new_seg_ds_seg.pkl bu04bk04_sc_1812_seg.pkl gy07bu07_1802_seg.pkl br08pk08_1812_seg.pkl ye04gr05_1812_seg.pkl"
CLASS_PKLS="bird1_new_class_ds_class.pkl bu04bk04_sc_1812_merged_class.pkl gy07bu07_1812_merged_class.pkl br08pk08_1812_merged_class.pkl ye04gr05_1812_merged_class.pkl"

# Convert to arrays
BIRD_ARR=($BIRDS)
SEG_ARR=($SEG_PKLS)
CLASS_ARR=($CLASS_PKLS)

# ── Helpers ───────────────────────────────────────────────────────────
vm_name() { echo "moove-train-$1"; }

get_seg_pkl() {
  for i in "${!BIRD_ARR[@]}"; do
    if [ "${BIRD_ARR[$i]}" = "$1" ]; then echo "${SEG_ARR[$i]}"; return; fi
  done
}

get_class_pkl() {
  for i in "${!BIRD_ARR[@]}"; do
    if [ "${BIRD_ARR[$i]}" = "$1" ]; then echo "${CLASS_ARR[$i]}"; return; fi
  done
}

# ══════════════════════════════════════════════════════════════════════
# SETUP: Upload code + PKLs + WAV data to GCS
# ══════════════════════════════════════════════════════════════════════
cmd_setup() {
  echo "=== Creating bucket $BUCKET ==="
  gcloud storage buckets create "$BUCKET" --location=europe-west4 2>/dev/null || true

  echo "=== Uploading code ==="
  tar czf /tmp/moove_code.tar.gz \
    -C "$REPO_DIR/.." \
    --exclude='*.pyc' --exclude='__pycache__' \
    --exclude='.venv' --exclude='venv' --exclude='.git' \
    --exclude='paper_experiments/results' \
    --exclude='paper_experiments/results_backup_*' \
    --exclude='new_plots' \
    "$(basename "$REPO_DIR")"
  gcloud storage cp /tmp/moove_code.tar.gz "$BUCKET/code/"
  rm /tmp/moove_code.tar.gz

  echo "=== Uploading training data (PKLs) ==="
  for bird in ${BIRDS}; do
    seg_pkl=$(get_seg_pkl "$bird")
    class_pkl=$(get_class_pkl "$bird")
    for pkl in "$seg_pkl" "$class_pkl"; do
      src="$TRAINING_DATA_DIR/$pkl"
      if [ -f "$src" ]; then
        echo "  Uploading $pkl ($(du -sh "$src" | cut -f1))..."
        gcloud storage cp "$src" "$BUCKET/data/" --no-clobber 2>/dev/null || echo "  (already exists, skipping)"
      else
        echo "  WARNING: $src not found!"
      fi
    done
  done

  echo ""
  echo "=== Uploading WAV data (for energy baseline) ==="
  for bird in ${BIRDS}; do
    bird_dir="$REC_DATA_DIR/$bird"
    if [ -d "$bird_dir" ]; then
      echo "  Uploading $bird WAVs ($(du -sh "$bird_dir" | cut -f1))..."
      gcloud storage cp -r "$bird_dir" "$BUCKET/rec_data/" --no-clobber 2>/dev/null || echo "  (already exists, skipping)"
    else
      echo "  WARNING: $bird_dir not found!"
    fi
  done

  echo ""
  echo "=== Setup complete. Total in bucket: ==="
  gcloud storage du -s "$BUCKET"
}

# ══════════════════════════════════════════════════════════════════════
# LAUNCH: Create 5 training VMs + 1 energy baseline VM
# ══════════════════════════════════════════════════════════════════════
cmd_launch() {
  # ── Training VMs (one per bird) ───────────────────────────────────
  for bird in ${BIRDS}; do
    name=$(vm_name "$bird")
    seg_pkl=$(get_seg_pkl "$bird")
    class_pkl=$(get_class_pkl "$bird")

    echo "=== Launching $name for $bird ==="

    cat > /tmp/startup_${bird}.sh << EOF
#!/bin/bash
set -eo pipefail
exec > /var/log/moove-training.log 2>&1
echo "=== Starting training at \$(date) ==="

BIRD="${bird}"
BUCKET="${BUCKET}"
SEG_PKL="${seg_pkl}"
CLASS_PKL="${class_pkl}"
PROJECT="${PROJECT}"
ZONE="${ZONE}"
VM_NAME="${name}"

# Install dependencies
apt-get update -qq
apt-get install -y -qq python3-pip python3-venv
pip3 install --quiet --break-system-packages torch torchvision numpy scipy scikit-learn tensorboard matplotlib seaborn pandas

# Download code
mkdir -p /opt/moove
cd /opt/moove
gcloud storage cp "\$BUCKET/code/moove_code.tar.gz" .
tar xzf moove_code.tar.gz
cd moove

# Download training data
mkdir -p /root/.moove/training_data
gcloud storage cp "\$BUCKET/data/\$SEG_PKL" /root/.moove/training_data/
gcloud storage cp "\$BUCKET/data/\$CLASS_PKL" /root/.moove/training_data/

echo "=== Data downloaded, starting training at \$(date) ==="

# Run experiments for this bird only (3 seeds x seg + class)
python3 -m paper_experiments.run_all --birds "\$BIRD" 2>&1 | tee /var/log/moove-run.log

echo "=== Training complete at \$(date) ==="

# Upload results
gcloud storage cp -r paper_experiments/results/ "\$BUCKET/results/\$BIRD/"

# Upload log
gcloud storage cp /var/log/moove-training.log "\$BUCKET/logs/\${BIRD}.log"
gcloud storage cp /var/log/moove-run.log "\$BUCKET/logs/\${BIRD}_run.log"

echo "=== Results uploaded. Self-deleting VM at \$(date) ==="
gcloud compute instances delete "\$VM_NAME" --zone="\$ZONE" --project="\$PROJECT" --quiet
EOF

    gcloud compute instances create "$name" \
      --zone="$ZONE" \
      --machine-type="$MACHINE_TYPE" \
      --boot-disk-size=50GB \
      --image-family=debian-12 \
      --image-project=debian-cloud \
      --scopes=storage-full,compute-rw \
      --metadata-from-file=startup-script=/tmp/startup_${bird}.sh \
      --no-restart-on-failure

    rm /tmp/startup_${bird}.sh
    echo "  -> $name created (SPOT, auto-deletes when done)"
  done

  # ── Energy Baseline VM ────────────────────────────────────────────
  echo ""
  echo "=== Launching moove-train-baseline (energy baseline) ==="

  cat > /tmp/startup_baseline.sh << EOF
#!/bin/bash
set -eo pipefail
exec > /var/log/moove-training.log 2>&1
echo "=== Starting energy baseline at \$(date) ==="

BUCKET="${BUCKET}"
PROJECT="${PROJECT}"
ZONE="${ZONE}"
VM_NAME="moove-train-baseline"

# Install dependencies
apt-get update -qq
apt-get install -y -qq python3-pip python3-venv libsndfile1
pip3 install --quiet --break-system-packages numpy scipy scikit-learn evfuncs

# Download code
mkdir -p /opt/moove
cd /opt/moove
gcloud storage cp "\$BUCKET/code/moove_code.tar.gz" .
tar xzf moove_code.tar.gz
cd moove

# Download WAV data (all birds)
mkdir -p /root/.moove/rec_data
gcloud storage cp -r "\$BUCKET/rec_data/" /root/.moove/rec_data/

echo "=== WAV data downloaded, starting baseline at \$(date) ==="

# Run energy baseline
python3 new_plots/figure_4/energy_baseline.py 2>&1 | tee /var/log/moove-baseline.log

echo "=== Baseline complete at \$(date) ==="

# Upload results
gcloud storage cp new_plots/figure_4/baseline_results.json "\$BUCKET/results/baseline/"
gcloud storage cp /var/log/moove-training.log "\$BUCKET/logs/baseline.log"
gcloud storage cp /var/log/moove-baseline.log "\$BUCKET/logs/baseline_run.log"

echo "=== Results uploaded. Self-deleting VM at \$(date) ==="
gcloud compute instances delete "\$VM_NAME" --zone="\$ZONE" --project="\$PROJECT" --quiet
EOF

  gcloud compute instances create "moove-train-baseline" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --provisioning-model=SPOT \
    --instance-termination-action=DELETE \
    --boot-disk-size=50GB \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --scopes=storage-full,compute-rw \
    --metadata-from-file=startup-script=/tmp/startup_baseline.sh \
    --no-restart-on-failure

  rm /tmp/startup_baseline.sh
  echo "  -> moove-train-baseline created (SPOT, auto-deletes when done)"

  echo ""
  echo "=== All 6 VMs launched (5 training + 1 baseline) ==="
  echo "=== Use 'bash gcloud_run.sh status' to check progress ==="
}

# ══════════════════════════════════════════════════════════════════════
# STATUS: Check which VMs are still running + which results exist
# ══════════════════════════════════════════════════════════════════════
cmd_status() {
  echo "=== VM Status ==="
  gcloud compute instances list --filter="name~moove-train" --format="table(name,status,zone)" 2>/dev/null || echo "No VMs found (all done?)"

  echo ""
  echo "=== Results in GCS ==="
  gcloud storage ls "$BUCKET/results/" 2>/dev/null || echo "No results yet"

  echo ""
  echo "=== Logs ==="
  gcloud storage ls "$BUCKET/logs/" 2>/dev/null || echo "No logs yet"
}

# ══════════════════════════════════════════════════════════════════════
# COLLECT: Download results from GCS to local
# ══════════════════════════════════════════════════════════════════════
cmd_collect() {
  echo "=== Downloading training results ==="
  for bird in ${BIRDS}; do
    echo "  Downloading $bird results..."
    gcloud storage cp -r "$BUCKET/results/$bird/results/" paper_experiments/ 2>/dev/null \
      && echo "  -> $bird done" \
      || echo "  -> $bird: no results yet"
  done

  echo ""
  echo "=== Downloading baseline results ==="
  gcloud storage cp "$BUCKET/results/baseline/baseline_results.json" new_plots/figure_4/ 2>/dev/null \
    && echo "  -> baseline done" \
    || echo "  -> baseline: no results yet"

  echo ""
  echo "=== Downloaded results: ==="
  find paper_experiments/results -name "results.json" 2>/dev/null | sort
  ls -la new_plots/figure_4/baseline_results.json 2>/dev/null || true
}

# ══════════════════════════════════════════════════════════════════════
# CLEANUP: Delete VMs + optionally bucket
# ══════════════════════════════════════════════════════════════════════
cmd_cleanup() {
  echo "=== Deleting any remaining VMs ==="
  for bird in ${BIRDS}; do
    name=$(vm_name "$bird")
    gcloud compute instances delete "$name" --zone="$ZONE" --quiet 2>/dev/null \
      && echo "  Deleted $name" \
      || echo "  $name already gone"
  done
  gcloud compute instances delete "moove-train-baseline" --zone="$ZONE" --quiet 2>/dev/null \
    && echo "  Deleted moove-train-baseline" \
    || echo "  moove-train-baseline already gone"

  echo ""
  read -p "Also delete GCS bucket $BUCKET? (y/N) " confirm
  if [ "$confirm" = "y" ]; then
    gcloud storage rm -r "$BUCKET"
    echo "Bucket deleted."
  else
    echo "Bucket kept. Delete later with: gcloud storage rm -r $BUCKET"
  fi
}

# ══════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════
case "${1:-help}" in
  setup)   cmd_setup ;;
  launch)  cmd_launch ;;
  status)  cmd_status ;;
  collect) cmd_collect ;;
  cleanup) cmd_cleanup ;;
  *)
    echo "Usage: bash gcloud_run.sh {setup|launch|status|collect|cleanup}"
    echo ""
    echo "  setup   — Upload code + PKLs + WAVs to GCS bucket"
    echo "  launch  — Create 6 VMs (5 training + 1 baseline), auto-delete when done"
    echo "  status  — Check which VMs are running + results in GCS"
    echo "  collect — Download results from GCS to local"
    echo "  cleanup — Delete remaining VMs, optionally bucket"
    ;;
esac
