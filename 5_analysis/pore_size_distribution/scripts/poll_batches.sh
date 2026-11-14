#!/bin/bash
# Polls both GPU batch checkpoint files, emitting one line per newly-completed
# job, and a final "ALL_DONE" or "FAILURES_PRESENT" line when both batches
# have processed all expected jobs (25 total: 16 GPU0 + 9 GPU1).
CKPT0="/c/Users/rony.schwartz/Documents/nnUNet4SoilXrayCT/05_evaluation/psd/fig4_inference_20260815/checkpoint_gpu0.json"
CKPT1="/c/Users/rony.schwartz/Documents/nnUNet4SoilXrayCT/05_evaluation/psd/fig4_inference_20260815/checkpoint_gpu1.json"
EXPECTED_TOTAL=25
seen=""

while true; do
  cur=$(python -c "
import json, os
seen_names=[]
for p in [r'$CKPT0', r'$CKPT1']:
    if os.path.exists(p):
        d = json.load(open(p))
        for k, v in d.items():
            if v.get('status') in ('done','failed'):
                seen_names.append(f\"{k}:{v['status']}\")
print('|'.join(seen_names))
" 2>/dev/null)

  IFS='|' read -ra items <<< "$cur"
  for item in "${items[@]}"; do
    [ -z "$item" ] && continue
    if [[ "$seen" != *"|$item|"* ]]; then
      seen="${seen}|${item}|"
      echo "DONE: $item"
    fi
  done

  n_done=$(python -c "
import json, os
n=0
for p in [r'$CKPT0', r'$CKPT1']:
    if os.path.exists(p):
        d = json.load(open(p))
        n += sum(1 for v in d.values() if v.get('status') in ('done','failed'))
print(n)
" 2>/dev/null)

  n_failed=$(python -c "
import json, os
n=0
for p in [r'$CKPT0', r'$CKPT1']:
    if os.path.exists(p):
        d = json.load(open(p))
        n += sum(1 for v in d.values() if v.get('status') == 'failed')
print(n)
" 2>/dev/null)

  if [ "$n_done" -ge "$EXPECTED_TOTAL" ]; then
    if [ "$n_failed" -gt 0 ]; then
      echo "FAILURES_PRESENT: $n_failed job(s) failed, $n_done/$EXPECTED_TOTAL total processed"
    else
      echo "ALL_DONE: $n_done/$EXPECTED_TOTAL jobs completed successfully"
    fi
    break
  fi
  sleep 90
done
