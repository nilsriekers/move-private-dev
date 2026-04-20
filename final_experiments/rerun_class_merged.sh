#!/bin/bash
# ══════════════════════════════════════════════════════════════════════
# Re-run classification training for birds that need label merging.
#
# bu04bk04:  b → i              (11 → 10 classes)
# br08pk08:  i→a, k→a, l→e, m→b (12 → 8 classes)
# ye04gr05:  i→b, j→b           (10 → 8 classes)
#
# merge_labels is configured in config.py; this script just triggers
# the training runs with --force to overwrite previous results.
# ══════════════════════════════════════════════════════════════════════
set -euo pipefail
cd "$(dirname "$0")/.."

for BIRD in bu04bk04 br08pk08 ye04gr05; do
    echo "══════════════════════════════════════════════════"
    echo "  Classification: $BIRD (3 seeds)"
    echo "══════════════════════════════════════════════════"
    uv run python3 final_experiments/run_all.py --bird "$BIRD" --type class --force
done

echo ""
echo "Done. All 3 birds re-trained with merged labels."
