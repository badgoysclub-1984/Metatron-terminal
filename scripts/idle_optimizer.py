#!/usr/bin/env python3
"""
METATRON OS — idle_optimizer.py
Continuous optimization loop for Metatron OS.

This script fulfills the requirement to continuously improve and optimize Metatron OS
whenever idle, by running dataset augmentation, model training (with self-optimization),
and exporting the updated model.
"""

import time
import subprocess
import os
from pathlib import Path

def run_loop():
    print("🧿 Starting Idle Optimization Loop for Metatron OS...", flush=True)
    
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    while True:
        try:
            print("\n" + "="*50, flush=True)
            print("⏳ [Phase 1] Augmenting Dataset via LLM router...", flush=True)
            # Generate 5 new data points per cycle
            subprocess.run(
                ["venv/bin/python", "scripts/augment_z9_data.py", "5"],
                check=True
            )
            
            print("\n⏳ [Phase 2] Training Model (Augmented Data + Self-Optimization)...", flush=True)
            # Train for a limited number of steps so the loop remains responsive
            subprocess.run(
                ["venv/bin/python", "z9_qat_training.py", "augmented", "--steps", "150"],
                check=True
            )
            
            print("\n⏳ [Phase 3] Exporting updated Z9 Model to Ollama Modelfile...", flush=True)
            subprocess.run(
                ["venv/bin/python", "z9_qat_training.py", "export"],
                check=True
            )
            
            print("\n✅ Loop iteration complete. Z9 Golden Triadic optimization applied.", flush=True)
            print("💤 Sleeping for 60 seconds before the next iteration...", flush=True)
            time.sleep(60)
            
        except subprocess.CalledProcessError as e:
            print(f"\n⚠️ Error during optimization step: {e}", flush=True)
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n🧿 Idle optimization loop stopped by user.", flush=True)
            break
        except Exception as e:
            print(f"\n⚠️ Unexpected error: {e}", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    # Change dir to script's parent directory if needed
    os.chdir(Path(__file__).parent.parent)
    run_loop()
