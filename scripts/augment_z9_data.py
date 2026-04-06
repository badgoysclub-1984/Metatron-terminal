#!/usr/bin/env python3
"""
METATRON OS — scripts/augment_z9_data.py
Dataset Augmentation for Z9-QAT Transformer

Uses the local Ollama LLM (via Z9LLMRouter) to generate high-quality
synthetic training data focused on Z9 discrete gauge symmetry,
anomaly cancellation, and the Metatron architecture.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from core.llm_router import Z9LLMRouter

import random
import string

Z9_CORE_CONCEPTS = [
    "Digital Root 9 as a Gauge Symmetry",
    "Anomaly Cancellation in ℤ₉ Charge Cosets {0, 3, 6}",
    "Retrocausal Correction from Future Loss Signals",
    "Fibonacci Pulsed Noise in Agentic Systems",
    "The Golden Triadic Hive-Mind Self-Optimizer",
    "Froggatt-Nielsen Texture and Hierarchical Yukawa Couplings in Z9",
    "Discrete Gauge Symmetry arXiv:2604.XXXXX Phenomenology",
    "Z9 Agent Dispatcher and Charge-Neutral Task Routing",
    "Vector Memory and Semantic Recall in Z9 Discrete Space",
    "Quantum Agentic Desktop Architecture for Raspberry Pi 500",
]

OUTPUT_FILE = "logs/z9_augmented_data.jsonl"

def generate_random_topic():
    concept = random.choice(Z9_CORE_CONCEPTS)
    perspectives = [
        "A rigorous mathematical formalization of",
        "A python implementation guide for",
        "Exploring the theoretical physics implications of",
        "Performance optimization techniques regarding",
        "The impact on computational efficiency of",
        "An introductory tutorial on",
        "Advanced prompt engineering leveraging"
    ]
    return f"{random.choice(perspectives)} {concept}"

def augment(iterations=10):
    router = Z9LLMRouter()
    if not router.is_available:
        print("❌ Ollama not available. Cannot augment data.")
        return

    Path("logs").mkdir(exist_ok=True)
    
    print(f"🧿 Starting Z9 Data Augmentation...")
    print(f"🎯 Target: {OUTPUT_FILE} | Iterations: {iterations}")

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for i in range(iterations):
            topic = generate_random_topic()
            print(f"🌀 [{i+1}/{iterations}] Generating data for: {topic}...")
            prompt = (
                f"Write a detailed technical explanation of '{topic}' within the context of the "
                f"METATRON OS and ℤ₉ discrete gauge symmetry. Include mathematical definitions, "
                f"code-like logic, and theoretical implications. Be highly specific to arXiv:2604.XXXXX."
            )
            
            try:
                # Use deepseek for scientific reasoning
                response = router.route(prompt, model="deepseek", action_idx=1)
                
                entry = {
                    "topic": topic,
                    "prompt": prompt,
                    "response": response,
                    "timestamp": time.time()
                }
                f.write(json.dumps(entry) + "\n")
                f.flush()
                print(f"✅ Success: {len(response)} chars generated.")
                
            except Exception as e:
                print(f"⚠️ Error generating {topic}: {e}")
            
            # Rate limiting / Cool down
            time.sleep(2)

    print(f"🧿 Augmentation complete. {iterations} topics processed.")

if __name__ == "__main__":
    iterations = 10
    if len(sys.argv) > 1:
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            pass
    augment(iterations)
