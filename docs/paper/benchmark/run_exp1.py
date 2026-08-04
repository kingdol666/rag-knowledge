#!/usr/bin/env python3
"""EXP-1: Retrieval Precision — fixed standalone runner"""
import json, time, statistics, math, sys
from pathlib import Path
from datetime import datetime, timezone
import urllib.request

BACKEND = "http://localhost:8765"
OUT_DIR = Path("d:/codes/ClaudeGPT/rag_project/rag-knowledge/docs/paper/benchmark/results")
OUT_DIR.mkdir(parents=True, exist_ok=True)
TIMEOUT = 15

def api_post(path, data):
    url = f"{BACKEND}/api/v1{path}"
    req = urllib.request.Request(url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}

KBS = {
    "AI-ML-Research": "4c1b9eb6-b8d3-498a-b8fa-f96cb7cdfd3b",
    "Energy-Batteries": "0a9d97c1-ecd2-4040-8690-253a0ac7ade8",
    "Materials-Science": "79c67037-481c-4213-b5b8-e684ecb6f6ba",
    "Biomedical-Engineering": "61960453-755c-4a4b-aa03-6d9453556572",
    "Embodied-AI": "4de920d8-b8c7-424e-a2fb-d73013f14bba",
    "Chemistry-Catalysis": "8bbd62eb-1c68-41fe-a981-66e18432cbeb",
}

QUERIES = []
for kb, qs in {
    "AI-ML-Research": [
        ("deep Q-network reinforcement learning Atari games experience replay", "DQN"),
        ("multi-head self-attention scaled dot-product transformer architecture", "transformer"),
        ("SHAP value explainable AI feature importance model interpretation", "SHAP"),
        ("retrieval augmented generation RAG knowledge-intensive NLP tasks", "RAG"),
        ("Adam optimizer adaptive moment estimation stochastic gradient descent", "Adam"),
    ],
    "Energy-Batteries": [
        ("battery thermal management phase change material liquid cooling PCM", "battery-thermal"),
        ("solid-state electrolyte lithium ion conductivity sulfide NASICON", "solid-state"),
        ("sodium ion battery cathode anode comparison LFP NMC", "sodium-ion"),
    ],
    "Materials-Science": [
        ("MXene Ti3C2Tx supercapacitor specific capacitance interlayer", "MXene"),
        ("machine learning interatomic potential DFT replacement materials", "machine-learning"),
        ("2D materials graphene transition metal dichalcogenide roadmap", "2D-materials"),
    ],
    "Biomedical-Engineering": [
        ("convolutional neural network medical imaging chest X-ray pneumonia", "medical-imaging"),
        ("wearable multimodal sensor motion detection accelerometer deep learning", "wearable"),
        ("intracranial EEG brain-computer interface neural recording implantable", "EEG"),
    ],
    "Embodied-AI": [
        ("humanoid robot loco-manipulation vision-language-action model", "VLA"),
        ("Sim-to-Real transfer domain randomization legged locomotion policy", "Sim-to-Real"),
        ("world model embodied AI Dreamer reinforcement learning planning", "world-model"),
    ],
    "Chemistry-Catalysis": [
        ("electrocatalysis hydrogen evolution reaction oxygen evolution overpotential", "electrocatalysis"),
        ("heterogeneous catalysis machine learning potential surface reaction barrier", "heterogeneous"),
        ("photocatalysis TiO2 fluoroalkylation ligand metal charge transfer", "photocatalysis"),
    ],
}.items():
    for q_text, doc_match in qs:
        QUERIES.append({"query": q_text, "correct_kb": kb, "kb_id": KBS[kb], "doc": doc_match})

print(f"EXP-1: {len(QUERIES)} queries across {len(KBS)} domains")

flat_p1s, flat_p3s, flat_p5s, domain_p1s, domain_p3s, domain_p5s = [], [], [], [], [], []
flat_fprs, domain_fprs = [], []
flat_mrrs, domain_mrrs = [], []
flat_ndcgs, domain_ndcgs = [], []
flat_lat, domain_lat = [], []

for i, q in enumerate(QUERIES):
    rel = q["doc"].lower()
    cid = q["kb_id"]
    
    # Flat search
    t0 = time.time()
    r = api_post("/search/vector", {"query": q["query"], "kb_id": "", "top_k": 5, "score_threshold": 0.0, "balance_kbs": False})
    flat_lat.append((time.time()-t0)*1000)
    
    # Domain search
    t0 = time.time()
    rd = api_post("/search/vector", {"query": q["query"], "kb_id": cid, "top_k": 5, "score_threshold": 0.0, "balance_kbs": False})
    domain_lat.append((time.time()-t0)*1000)
    
    fps = [x.get("doc_path","") for x in r.get("results",[])[:5]]
    fks = [x.get("kb_id","") for x in r.get("results",[])[:5]]
    dps = [x.get("doc_path","") for x in rd.get("results",[])[:5]]
    dks = [x.get("kb_id","") for x in rd.get("results",[])[:5]]
    
    def hit(ps, k): return sum(1 for p in ps[:k] if rel in p.lower())/k if k>0 else 0
    def rr(ps):
        for j,p in enumerate(ps):
            if rel in p.lower(): return 1/(j+1)
        return 0
    def ndcg(ps, k=5):
        dcg = sum((1/math.log2(j+2)) for j,p in enumerate(ps[:k]) if rel in p.lower())
        return dcg/(1/math.log2(2))
    def fpr(ks, k=5):
        return sum(1 for x in ks[:k] if x!=cid and x!="")/k
    
    flat_p1s.append(hit(fps,1)); flat_p3s.append(hit(fps,3)); flat_p5s.append(hit(fps,5))
    domain_p1s.append(hit(dps,1)); domain_p3s.append(hit(dps,3)); domain_p5s.append(hit(dps,5))
    flat_fprs.append(fpr(fks)); domain_fprs.append(fpr(dks))
    flat_mrrs.append(rr(fps)); domain_mrrs.append(rr(dps))
    flat_ndcgs.append(ndcg(fps)); domain_ndcgs.append(ndcg(dps))
    
    if (i+1) % 5 == 0:
        mf = statistics.mean(flat_p5s[:i+1])
        md = statistics.mean(domain_p5s[:i+1])
        print(f"  [{i+1}/{len(QUERIES)}] Flat P@5={mf:.3f} Domain P@5={md:.3f} (Δ={md-mf:+.3f})")

def m(v): return round(statistics.mean(v), 4)
def s(v): return round(statistics.stdev(v), 4) if len(v)>1 else 0

result = {
    "experiment": "EXP-1",
    "title": "Retrieval Precision Main Experiment",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "n_queries": len(QUERIES),
    "n_domains": len(KBS),
    "search_space_total": 13709,
    "methods": {
        "B1_Vector_Flat": {
            "P@1": m(flat_p1s), "P@3": m(flat_p3s), "P@5": m(flat_p5s),
            "nDCG@5": m(flat_ndcgs), "MRR": m(flat_mrrs), "FPR": m(flat_fprs),
            "Candidates": 13709, "Latency_ms": m(flat_lat),
            "P@5_std": s(flat_p5s), "FPR_std": s(flat_fprs),
        },
        "QDCVR_Domain_ours": {
            "P@1": m(domain_p1s), "P@3": m(domain_p3s), "P@5": m(domain_p5s),
            "nDCG@5": m(domain_ndcgs), "MRR": m(domain_mrrs), "FPR": m(domain_fprs),
            "Candidates": "per-KB (~10-600)", "Latency_ms": m(domain_lat),
            "P@5_std": s(domain_p5s), "FPR_std": s(domain_fprs),
        }
    },
    "delta": {
        "P@5": round(m(domain_p5s) - m(flat_p5s), 4),
        "FPR_reduction_pct": round((1 - m(domain_fprs)/max(m(flat_fprs),0.001))*100, 1),
        "MRR_delta": round(m(domain_mrrs) - m(flat_mrrs), 4),
    },
    "raw": {
        "flat_p5": flat_p5s, "domain_p5": domain_p5s,
        "flat_fpr": flat_fprs, "domain_fpr": domain_fprs,
        "flat_mrr": flat_mrrs, "domain_mrr": domain_mrrs,
        "flat_ndcg": flat_ndcgs, "domain_ndcg": domain_ndcgs,
    }
}

(OUT_DIR / "EXP-1-retrieval-precision.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(f"\n{'='*70}")
print(f"EXP-1 RESULTS")
print(f"{'='*70}")
print(f"{'Metric':<15} {'Flat':>10} {'Domain':>10} {'Delta':>10}")
print(f"{'-'*45}")
for k in ["P@1","P@3","P@5","nDCG@5","MRR","FPR"]:
    fv = result["methods"]["B1_Vector_Flat"][k]
    dv = result["methods"]["QDCVR_Domain_ours"][k]
    delta = round(dv - fv, 4)
    print(f"{k:<15} {fv:>10.4f} {dv:>10.4f} {delta:>+10.4f}")
print(f"{'-'*45}")
print(f"Flat Latency: {result['methods']['B1_Vector_Flat']['Latency_ms']:.0f}ms")
print(f"Domain Latency: {result['methods']['QDCVR_Domain_ours']['Latency_ms']:.0f}ms")
print(f"FPR Reduction: {result['delta']['FPR_reduction_pct']}%")
