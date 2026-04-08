#!/usr/bin/env python3
"""
METATRON OS — Advanced Idle Optimizer
Runs continuously in the background to improve Metatron OS:
- Dataset generation (synthetic augmentation)
- Database optimization (VectorMemory re-indexing & deduplication)
- Training (Z9-QAT model tuning)
- Self-Optimization (Golden Triadic Hive-Mind steps)
- Computational improvements (Cache clearing, pyc compilation)
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.memory import VectorMemory
from core.self_optimizer import Z9GoldenTriadicSelfOptimizer
from z9_qat_training import SimpleTokenizer, build_augmented_data, Z9QATModel, Z9QATTrainer

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [IDLE-OPT] %(message)s",
                    handlers=[
                        logging.FileHandler(PROJECT_ROOT / "logs" / "advanced_optimizer.log"),
                        logging.StreamHandler()
                    ])
log = logging.getLogger("idle_opt")

def optimize_database():
    log.info("Optimizing Vector Database...")
    mem_path = PROJECT_ROOT / "config" / "vector_memory.json"
    if mem_path.exists():
        mem = VectorMemory(persist_path=mem_path)
        log.info(f"Loaded {len(mem)} memories. Re-indexing...")
        # Re-save forces a clean serialization (VectorMemory handles deduplication on search)
        # We can simulate compaction
        unique_texts = {}
        for emb, txt, meta in mem.memories:
            unique_texts[txt] = meta
        
        mem.memories = []
        if mem.index is not None:
            mem.index.reset()
            
        entries = [{"text": t, "metadata": m} for t, m in unique_texts.items()]
        mem.batch_add(entries, skip_save=False)
        log.info(f"Database optimized. {len(mem)} unique entries retained.")
    else:
        log.info("No vector database found to optimize.")

def augment_datasets():
    log.info("Augmenting synthetic datasets...")
    augment_script = PROJECT_ROOT / "scripts" / "augment_z9_data.py"
    if augment_script.exists():
        try:
            # Run augmentation script to generate 5 new samples
            subprocess.run([sys.executable, str(augment_script), "5"], check=True, cwd=str(PROJECT_ROOT))
            log.info("Dataset augmentation complete.")
        except subprocess.CalledProcessError as e:
            log.error(f"Dataset augmentation failed: {e}")
    else:
        log.warning(f"Augmentation script {augment_script} not found.")

def train_model():
    log.info("Running Z9-QAT Training...")
    tokenizer = SimpleTokenizer()
    model = Z9QATModel()
    
    # Load existing checkpoint if any
    ckpt_path = PROJECT_ROOT / "checkpoints" / "z9_qat_model.pth"
    if ckpt_path.exists():
        import torch
        try:
            ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
            if "model" in ckpt:
                model.load_state_dict(ckpt["model"])
            else:
                model.load_state_dict(ckpt)
            log.info("Loaded existing model checkpoint.")
        except Exception as e:
            log.warning(f"Could not load checkpoint, starting fresh. {e}")

    trainer = Z9QATTrainer(
        model, tokenizer,
        base_lr=3e-4,
        batch_size=8,
        seq_len=256,
        log_every=50,
        save_every=200,
        ckpt_dir=str(PROJECT_ROOT / "checkpoints")
    )
    
    data = build_augmented_data(tokenizer)
    log.info(f"Training on {len(data)} tokens for 200 steps...")
    trainer.train_epoch(data, steps=200)
    trainer.save("z9_qat_model.pth")
    log.info("Training complete.")
    
    # Export Modelfile
    try:
        subprocess.run([sys.executable, "z9_qat_training.py", "export"], check=True, cwd=str(PROJECT_ROOT))
        log.info("Modelfile exported.")
    except subprocess.CalledProcessError as e:
        log.error(f"Modelfile export failed: {e}")

def run_self_optimizer():
    log.info("Running Golden Triadic Self-Optimizer...")
    opt = Z9GoldenTriadicSelfOptimizer(config_path=str(PROJECT_ROOT / "config" / "metatron_config.json"))
    opt.start()
    time.sleep(15) # Allow it to take a couple of steps
    opt.stop()
    log.info("Self-Optimization step complete.")

def computational_improvements():
    log.info("Applying computational improvements...")
    try:
        # Precompile python files
        import compileall
        compileall.compile_dir(str(PROJECT_ROOT / "core"), force=True, quiet=1)
        compileall.compile_dir(str(PROJECT_ROOT / "agents"), force=True, quiet=1)
        # Clear unused memory
        import gc
        gc.collect()
        log.info("Computational improvements (compilation & GC) complete.")
    except Exception as e:
        log.error(f"Computational improvements failed: {e}")

def main():
    log.info("🧿 Metatron Advanced Idle Optimizer Started.")
    # Ensure logs directory exists
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    
    while True:
        try:
            log.info("=== Starting Optimization Cycle ===")
            augment_datasets()
            optimize_database()
            train_model()
            run_self_optimizer()
            computational_improvements()
            log.info("=== Cycle Complete. Sleeping for 10 minutes ===")
            time.sleep(600)
        except KeyboardInterrupt:
            log.info("Optimizer stopped by user.")
            break
        except Exception as e:
            log.error(f"Error in optimization cycle: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
