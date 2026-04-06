#!/bin/bash
# 🧿 METATRON DESKTOP — Idle Improvement Loop
# Continuously augments dataset, trains the Z9 model, and exports it

cd /home/badgoysclub/metatron-os-v3
mkdir -p logs

while true; do
    echo "[$(date)] 🧿 Starting continuous improvement cycle..." >> logs/idle_improvement.log

    # 1. Augment dataset (generate 5 new synthetic samples via local LLM)
    echo ">> Augmenting dataset..." >> logs/idle_improvement.log
    /home/badgoysclub/metatron-os-v3/venv/bin/python scripts/augment_z9_data.py 5 >> logs/idle_improvement.log 2>&1

    # 2. Train on augmented data
    echo ">> Training Z9 QAT model..." >> logs/idle_improvement.log
    /home/badgoysclub/metatron-os-v3/venv/bin/python z9_qat_training.py augmented --steps 200 >> logs/idle_improvement.log 2>&1

    # 3. Export new Modelfile
    echo ">> Exporting Modelfile..." >> logs/idle_improvement.log
    /home/badgoysclub/metatron-os-v3/venv/bin/python z9_qat_training.py export >> logs/idle_improvement.log 2>&1

    # Sleep for 5 minutes between cycles
    echo ">> Cycle complete. Cooling down for 5 minutes..." >> logs/idle_improvement.log
    sleep 300
done