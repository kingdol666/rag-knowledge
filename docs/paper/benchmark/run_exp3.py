#!/usr/bin/env python3
"""EXP-3: Multi-baseline comparison + EXP-7: Efficiency analysis"""
import json, time, statistics, math
from pathlib import Path
from datetime import datetime, timezone
import urllib.request

BACKEND = "http://localhost:8765"
OUT = Path("d:/codes/ClaudeGPT/rag_project/rag-knowledge/docs/paper/benchmark/results")
OUT.mkdir(parents=True, exist_ok=True)

def api_post(path, data):
    url = f"{BACKEND}/api/v1{path}"
    req = urllib.request.Request(url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"results": [], "error": str(e)}

QUERIES = [
    ("deep Q-network reinforcement learning Atari games experience replay", "4c1b9eb6-b8d3-498a-b8fa-f96cb7cdfd3b", "DQN"),
    ("battery thermal management phase change material liquid cooling PCM", "0a9d97c1-ecd2-4040-8690-253a0ac7ade8", "battery-thermal"),
    ("MXene Ti3C2Tx supercapacitor specific capacitance interlayer", "79c67037-481c-4213-b5b8-e684ecb6f6ba", "MXene"),
    ("convolutional neural network medical imaging chest X-ray pneumonia", "61960453-755c-4a4b-aa03-6d9453556572", "medical-imaging"),
    ("humanoid robot loco-manipulation vision-language-action model", "4de920d8-b8c7-424e-a2fb-d73013f14bba", "VLA"),
    ("electrocatalysis hydrogen evolution reaction oxygen evolution overpotential", "8bbd62eb-1c68-41fe-a981-66e18432cbeb", "electrocatalysis"),
    ("reinforcement learning optimization policy gradient materials design", "4c1b9eb6-b8d3-498a-b8fa-f96cb7cdfd3b", "Reinforcement"),
    ("graph neural network state estimation prediction time series", "4c1b9eb6-b8d3-498a-b8fa-f96cb7cdfd3b", "graph"),
    ("thermal management cooling heat transfer CFD", "0a9d97c1-ecd2-4040-8690-253a0ac7ade8", "battery"),
    ("machine learning healthcare diagnosis classification detection", "61960453-755c-4a4b-aa03-6d9453556572", "medical"),
]

methods = {
    "B1_Vector_Flat": {"kb_id": "", "two_stage": False},
    "QDCVR_Domain": {"kb_id": "per_query", "two_stage": False},
    "QDCVR_TwoStage": {"kb_id": "per_query", "two_stage": True},
}

method_results = {name: {"p5": [], "mrr": [], "fpr": [], "lat": [], "candidates": []} for name in methods}

print(f"EXP-3: Multi-baseline — {len(QUERIES)} queries × {len(methods)} methods")

for qi, (q, kb_id, rel_doc) in enumerate(QUERIES):
    rel = rel_doc.lower()
    
    for mname, mcfg in methods.items():
        kid = kb_id if mcfg["kb_id"] == "per_query" else ""
        t0 = time.time()
        
        if mcfg["two_stage"]:
            r = api_post("/search/two-stage", {"query": q, "kb_id": kid, "top_k": 5, "verify_content": False})
        else:
            r = api_post("/search/vector", {"query": q, "kb_id": kid, "top_k": 5, "score_threshold": 0.0})
        
        lat = (time.time()-t0)*1000
        ps = [x.get("doc_path","") for x in r.get("results",[])[:5]]
        ks = [x.get("kb_id","") for x in r.get("results",[])[:5]]
        
        hits = [1 if rel in p.lower() else 0 for p in ps]
        p5 = sum(hits)/5
        mrr_val = 0
        for j,h in enumerate(hits):
            if h: mrr_val = 1/(j+1); break
        fpr_val = sum(1 for k in ks if k != kb_id and k != "")/5
        cands = len(r.get("results",[]))
        
        method_results[mname]["p5"].append(p5)
        method_results[mname]["mrr"].append(mrr_val)
        method_results[mname]["fpr"].append(fpr_val)
        method_results[mname]["lat"].append(lat)
        method_results[mname]["candidates"].append(cands)
    
    if (qi+1) % 3 == 0:
        print(f"  [{qi+1}/{len(QUERIES)}] Flat={statistics.mean(method_results['B1_Vector_Flat']['p5']):.3f} Domain={statistics.mean(method_results['QDCVR_Domain']['p5']):.3f} 2Stage={statistics.mean(method_results['QDCVR_TwoStage']['p5']):.3f}")

exp3 = {
    "experiment": "EXP-3", "title": "Multi-Baseline Comprehensive Comparison",
    "timestamp": datetime.now(timezone.utc).isoformat(), "n_queries": len(QUERIES),
    "methods": {}
}
for mname in methods:
    res = method_results[mname]
    exp3["methods"][mname] = {
        "P@5": round(statistics.mean(res["p5"]), 4),
        "MRR": round(statistics.mean(res["mrr"]), 4),
        "FPR": round(statistics.mean(res["fpr"]), 4),
        "Latency_ms": round(statistics.mean(res["lat"]), 1),
        "Candidates": int(statistics.mean(res["candidates"])),
    }

(OUT / "EXP-3-multi-baseline.json").write_text(json.dumps(exp3, indent=2, ensure_ascii=False))

# Also save EXP-7 efficiency data
exp7 = {
    "experiment": "EXP-7", "title": "Efficiency & Latency Analysis",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "latency_breakdown": {
        "B1_Vector_Flat": exp3["methods"]["B1_Vector_Flat"]["Latency_ms"],
        "QDCVR_Domain": exp3["methods"]["QDCVR_Domain"]["Latency_ms"],
        "QDCVR_TwoStage": exp3["methods"]["QDCVR_TwoStage"]["Latency_ms"],
    },
    "efficiency_accuracy": {
        "Flat_P5_per_ms": round(exp3["methods"]["B1_Vector_Flat"]["P@5"] / max(exp3["methods"]["B1_Vector_Flat"]["Latency_ms"], 0.1) * 1000, 2),
        "Domain_P5_per_ms": round(exp3["methods"]["QDCVR_Domain"]["P@5"] / max(exp3["methods"]["QDCVR_Domain"]["Latency_ms"], 0.1) * 1000, 2),
        "TwoStage_P5_per_ms": round(exp3["methods"]["QDCVR_TwoStage"]["P@5"] / max(exp3["methods"]["QDCVR_TwoStage"]["Latency_ms"], 0.1) * 1000, 2),
    }
}
(OUT / "EXP-7-efficiency-latency.json").write_text(json.dumps(exp7, indent=2, ensure_ascii=False))

print(f"\n{'='*70}")
print(f"EXP-3/7 Results")
print(f"{'='*70}")
for mname in methods:
    m = exp3["methods"][mname]
    print(f"{mname:<20} P@5={m['P@5']:.3f} FPR={m['FPR']:.3f} MRR={m['MRR']:.3f} Lat={m['Latency_ms']:.0f}ms")
print(f"\nEfficiency: Flat={exp7['efficiency_accuracy']['Flat_P5_per_ms']} Domain={exp7['efficiency_accuracy']['Domain_P5_per_ms']} 2Stage={exp7['efficiency_accuracy']['TwoStage_P5_per_ms']} P@5/ms×1000")
