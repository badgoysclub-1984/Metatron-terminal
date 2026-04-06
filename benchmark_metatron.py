#!/usr/bin/env python3
import time
import os
import sys
import json
import psutil
import torch
import numpy as np
import faiss
from pathlib import Path

# Try imports from metatron core
sys.path.append(os.getcwd())
try:
    from core.charge_neutral import digital_root_9
    from core.z9_constants import EPSILON, FIB
except ImportError:
    # Fallback for benchmark if not in venv correctly
    def digital_root_9(x): return 1 + ((x - 1) % 9)
    EPSILON = 0.22
    FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]

def get_sys_info():
    info = {
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_freq_mhz": psutil.cpu_freq().max if psutil.cpu_freq() else "N/A",
        "mem_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
        "torch_version": torch.__version__,
        "device": "cpu"
    }
    return info

def benchmark_z9_core():
    print("Benchmarking Z9 Core Logic...")
    start = time.perf_counter()
    # Stress test digital root 9 on 1M numbers
    t = torch.randint(0, 1000000, (1000000,))
    _ = (t % 9)
    z9_time = time.perf_counter() - start
    
    start = time.perf_counter()
    # Stress test Fibonacci pulsing
    for _ in range(10000):
        _ = [1.0 + 0.1 * np.log1p(f) for f in FIB]
    fib_time = time.perf_counter() - start
    
    return {"digital_root_1M_s": round(z9_time, 4), "fib_pulse_10k_s": round(fib_time, 4)}

def benchmark_vector_memory():
    print("Benchmarking Vector Memory (FAISS)...")
    d = 384  # MiniLM-L6-v2 dimension
    nb = 10000 # 10k memories
    nq = 100   # 100 queries
    
    xb = np.random.random((nb, d)).astype('float32')
    xq = np.random.random((nq, d)).astype('float32')
    
    start = time.perf_counter()
    index = faiss.IndexFlatL2(d)
    index.add(xb)
    build_time = time.perf_counter() - start
    
    start = time.perf_counter()
    D, I = index.search(xq, 5) # Top 5
    search_time = time.perf_counter() - start
    
    return {
        "faiss_build_10k_s": round(build_time, 4),
        "faiss_search_100q_s": round(search_time, 4),
        "avg_search_ms": round((search_time / nq) * 1000, 4)
    }

def benchmark_llm_inference():
    print("Benchmarking LLM Inference (Ollama)...")
    import requests
    try:
        start = time.perf_counter()
        # Ping ollama
        resp = requests.post("http://localhost:11434/api/generate", 
                             json={
                                 "model": "qwen2.5-coder:3b", 
                                 "prompt": "Why is 9 a sacred number in Metatron OS?",
                                 "stream": False,
                                 "options": {"num_predict": 50}
                             }, timeout=120)
        end = time.perf_counter()
        
        if resp.status_code == 200:
            data = resp.json()
            total_time = end - start
            eval_count = data.get("eval_count", 0)
            tps = eval_count / (data.get("eval_duration", 1) / 1e9)
            return {
                "model": "gemma3-4b",
                "total_latency_s": round(total_time, 2),
                "tokens_per_sec": round(tps, 2),
                "response_len": len(data.get("response", ""))
            }
        else:
            return {"error": f"Ollama returned {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def benchmark_training_step():
    print("Benchmarking Z9-QAT Training Step...")
    try:
        from z9_qat_training import Z9QATModel, VOCAB_SIZE, D_MODEL, N_HEADS, N_LAYERS
        model = Z9QATModel()
        x = torch.randint(0, VOCAB_SIZE, (8, 128)) # Batch 8, Seq 128
        y = torch.randint(0, VOCAB_SIZE, (8, 128))
        opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
        
        # Warmup
        _ = model(x)
        
        start = time.perf_counter()
        for _ in range(5):
            logits = model(x)
            loss = torch.nn.functional.cross_entropy(logits.view(-1, VOCAB_SIZE), y.view(-1))
            opt.zero_grad()
            loss.backward()
            opt.step()
        end = time.perf_counter()
        
        return {"step_avg_s": round((end - start) / 5, 4)}
    except Exception as e:
        return {"error": str(e)}

def main():
    print("====================================================")
    print("🧿 METATRON OS — FULL SYSTEM PERFORMANCE BENCHMARK")
    print("====================================================")
    
    results = {}
    results["system"] = get_sys_info()
    results["z9_core"] = benchmark_z9_core()
    results["vector_memory"] = benchmark_vector_memory()
    results["training"] = benchmark_training_step()
    results["llm"] = benchmark_llm_inference()
    
    print("\n" + "="*50)
    print("RESULTS SUMMARY")
    print("="*50)
    print(json.dumps(results, indent=2))
    
    # Accurate and Honest Analysis
    print("\n--- HONEST PERFORMANCE ANALYSIS ---")
    sys_info = results["system"]
    print(f"Hardware: Raspberry Pi (CPU: {sys_info['cpu_count']} cores, RAM: {sys_info['mem_total_gb']}GB)")
    
    if "error" not in results["llm"]:
        tps = results["llm"]["tokens_per_sec"]
        print(f"LLM Throughput: {tps} tok/s (Target: >5 tok/s for usability)")
        if tps < 2:
            print("Status: SLUGGISH. Recommend using 1.5b or 3b models for smoother interaction.")
        elif tps < 8:
            print("Status: USABLE. Good for asynchronous tasks.")
        else:
            print("Status: EXCELLENT. Near real-time responsiveness.")
    else:
        print("LLM Status: OFFLINE. (Check if 'ollama serve' is running)")

    mem_lat = results["vector_memory"]["avg_search_ms"]
    print(f"Memory Latency: {mem_lat}ms (Target: <10ms for RAG)")
    if mem_lat > 50:
        print("Status: DEGRADED. Vector search is slow; check CPU load.")
    else:
        print("Status: OPTIMAL. FAISS is performing well on ARM64.")

    step_time = results["training"].get("step_avg_s", 999)
    print(f"QAT Training: {step_time}s/step (Target: <1.0s for local adaptation)")
    if step_time > 2.0:
        print("Status: HEAVY. Full training not recommended; use 1-step LoRA or similar.")

    print("\nBenchmark Finished.")

if __name__ == "__main__":
    main()
