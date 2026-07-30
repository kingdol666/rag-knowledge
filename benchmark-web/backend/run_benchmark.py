"""
Standalone benchmark runner — BM25 + QDCVR comparison.
No BGE-M3 dependency. Uses rank_bm25 directly.
"""
import json, os, re, time, requests
import numpy as np
from rank_bm25 import BM25Okapi

os.chdir("D:/codes/ClaudeGPT/rag_project/rag-knowledge/benchmark-web/backend")
os.makedirs("results/raw", exist_ok=True)

# ── Documents ──
DOCS = []
def add(id, title, domain, content):
    DOCS.append({"id":id,"title":title,"domain":domain,"content":content})

add("dqn","Human-Level Control through Deep RL","AI-ML-Research","Deep Q-Network combines Q-learning with deep neural networks. Experience replay buffer stores transitions sampling random minibatches to break temporal correlations. Target network periodically updated. Evaluated 49 Atari 2600 games surpassing human performance on 23. Convolutional neural network processes raw pixels. RMSProp optimizer learning rate 0.00025.")
add("transformer","Attention Is All You Need","AI-ML-Research","Transformer uses multi-head self-attention mechanism. Scaled dot-product attention softmax QK transpose over sqrt d_k times V. Multi-head concat of attention heads. Positional encoding sine cosine functions. Achieved 28.4 BLEU on WMT 2014 translation task. Adam optimizer beta1 0.9 beta2 0.98. Dropout rate 0.1 applied to attention weights.")
add("rag","Retrieval-Augmented Generation","AI-ML-Research","RAG combines parametric memory seq2seq model with non-parametric memory dense vector index of Wikipedia. Two variants RAG-Sequence same document whole sequence RAG-Token different documents per token. Dense Passage Retriever DPR with BERT-base encoder top-k equals 5. BART-large generator. Outperforms BART on Open-domain QA Natural Questions 44.5 EM and FEVER fact verification.")
add("shap","SHAP Explainable AI Feature Importance","AI-ML-Research","SHAP SHapley Additive exPlanations assigns feature importance using Shapley values from cooperative game theory. Satisfies three properties local accuracy missingness consistency. Kernel SHAP approximates via linear LIME with special weighting kernel. Tree SHAP computes exact values for tree ensembles O of TLD squared time. Deep SHAP combines DeepLIFT with Shapley values.")
add("adam","Adam Method for Stochastic Optimization","AI-ML-Research","Adam combines RMSProp and momentum. Maintains exponential moving averages of gradients m_t and squared gradients v_t. Bias-corrected estimates m_hat equals m_t divided by 1 minus beta1 power t. Default hyperparameters alpha 0.001 beta1 0.9 beta2 0.999 epsilon 1e-8. Evaluated on MNIST CIFAR-10 IMDB sentiment. Converges faster than SGD with momentum and AdaGrad.")

add("battery-thermal","Battery Thermal Management Using PCM","Energy-Batteries","Phase change materials PCMs absorb latent heat during melting maintaining temperature near melting point. Paraffin wax melting point 40 to 50 Celsius and fatty acids used for Li-ion battery thermal management. Hybrid systems combine PCM with liquid cooling channels for higher heat dissipation rates. Battery temperature reduced by 15 to 20 Celsius under 3C discharge rate. Copper foam PCM composites improve effective thermal conductivity from 0.2 to 5 to 10 Watt per meter Kelvin.")
add("solid-state","Solid-State Electrolytes for Lithium Batteries","Energy-Batteries","Solid-state electrolytes replace liquid electrolytes for improved safety and energy density. Three main classes oxide LLZO LATP, sulfide LGPS Li6PS5Cl, and polymer PEO-LiTFSI. LLZO Li7La3Zr2O12 achieves ionic conductivity of 1e-3 Siemens per centimeter comparable to liquid electrolytes. Interface challenges lithium dendrite growth through grain boundaries and space charge layer effects. Full cells with NMC811 cathode achieve over 1000 cycles.")
add("na-ion","Sodium-Ion Batteries as Sustainable Alternatives","Energy-Batteries","Sodium-ion batteries use abundant Na instead of Li. Hard carbon anode provides about 300 milliamp hours per gram capacity. Cathode materials layered oxides Na_xMO2 with M equals Ni Mn Co Fe, Prussian blue analogs Na2M Fe CN 6, and polyanionic compounds Na3V2 PO4 2F3. P2-Na2/3 Ni1/3Mn2/3 O2 achieves 160 mAh per gram with good cycling stability. Cost advantage Na2CO3 at 0.15 dollars per kg vs Li2CO3 at 12 dollars per kg.")
add("supercapacitor","Carbon Nanoarchitectures for Supercapacitors","Energy-Batteries","Supercapacitors store energy via electrical double-layer capacitance EDLC and pseudocapacitance. Carbon nanomaterials activated carbon 1000 to 3000 square meters per gram, graphene theoretical 2630, carbon nanotubes. MXene Ti3C2Tx achieves volumetric capacitance of 1500 Farads per cubic centimeter. Hierarchical porous structures micropores under 2nm mesopores 2 to 50nm macropores over 50nm. Cycling stability over 100000 cycles versus under 5000 for batteries.")
add("soc-estimation","GNN for Battery State of Charge Estimation","Energy-Batteries","Graph neural networks GNNs estimate battery state of charge SOC from voltage current temperature sequences. Battery cells modeled as graph nodes spatial-temporal GNN captures cell-to-cell variations in battery pack. Gated GCN with attention mechanism weights connected cells. Training data 2000 charge-discharge cycles at 1 Hertz. Output SOC 0 to 100 percent with MAE under 1.5 percent. Outperforms LSTM MAE 3.2 percent and Kalman filter MAE 5 percent. Model compression via 8-bit quantization for BMS deployment.")

add("mxene","MXene Ti3C2Tx for Supercapacitors","Materials-Science","MXene Ti3C2Tx synthesized by selective etching of Al from Ti3AlC2 MAX phase using HF or LiF HCl. Accordion-like layered structure with interlayer spacing of 1.0 to 1.5 nanometers. Surface terminations Tx equals O OH F contribute pseudocapacitance via protonation deprotonation. Specific capacitance 245 Farads per gram at 2 millivolt per second in 1M H2SO4. Volumetric capacitance 1500 Farads per cubic centimeter exceeding carbon materials. 10000 cycles with over 90 percent capacitance retention.")
add("ml-potentials","ML Interatomic Potentials for Materials Simulation","Materials-Science","ML interatomic potentials replace DFT for million-atom simulations. Descriptors SOAP Smooth Overlap of Atomic Positions, ACSF Atom-Centered Symmetry Functions, moment tensor potentials. Neural network architectures Behler-Parrinello atom-centered, SchNet continuous-filter convolution, MACE equivariant message passing. Training data from DFT PBE SCAN functional with 10^4 to 10^6 configurations. Accuracy forces under 50 millielectronvolt per Angstrom energies under 5 meV per atom. Applications phase transitions defect migration dislocation dynamics grain boundary sliding.")
add("2d-roadmap","2D Materials Roadmap Beyond Graphene","Materials-Science","Two-dimensional materials beyond graphene include transition metal dichalcogenides TMDs MoS2 WS2 WSe2, hexagonal boron nitride h-BN, black phosphorus phosphorene, and MXenes. TMDs exhibit thickness-dependent bandgap transition from indirect to direct MoS2 1.29 eV indirect bulk to 1.90 eV direct monolayer. h-BN as ideal dielectric substrate with atomically flat surface. Heterostructures via van der Waals stacking. Twistronics magic angle bilayer graphene shows superconductivity at 1.1-degree twist.")
add("graphene-fabric","Graphene-MXene Flexible Fabric Sensors","Materials-Science","Wearable fabric sensors integrate graphene oxide GO and MXene nanosheets into cotton polyester textiles. Dip-coating process fabric immersed in GO dispersion 2 mg per mL for 30 minutes reduced with hydrazine vapor at 90 Celsius for 12 hours. MXene Ti3C2Tx applied via spray coating at 1 mg per square centimeter loading. Piezoresistive response gauge factor of 25 at 5 percent strain. Applications human motion detection finger bending knee flexion respiration monitoring chest expansion pulse wave detection. 200 wash cycles with under 10 percent performance degradation.")
add("metamaterials","Damage-Programmable Mechanical Metamaterials","Materials-Science","Mechanical metamaterials with programmable damage pathways via engineered void patterns. Unit cell design using topology optimization with objective to maximize energy absorption while controlling failure sequence. 3D printed via stereolithography resin or selective laser melting Ti-6Al-4V. Void aspect ratio controls buckling versus fracture transition. Hierarchical designs microscale voids within macroscale lattice struts. Energy absorption 40 Megajoule per cubic meter. Applications crashworthiness automotive crumple zones blast protection reusable impact absorbers.")

add("medical-cnn","CNN for Chest X-Ray Pneumonia Detection","Biomedical-Engineering","Convolutional neural networks detect pneumonia from chest X-ray images. DenseNet-121 pretrained on ImageNet fine-tuned on ChestX-ray14 dataset 112120 images. Achieves AUROC of 0.85 for pneumonia detection matching radiologist performance. Class activation maps CAM highlight affected lung regions for interpretability. Data augmentation random rotation plus minus 10 degrees horizontal flip brightness contrast jitter. Two-stage pipeline lung segmentation via U-Net then pneumonia classification. Ensemble of 5 models improves AUROC to 0.88. Deployed as web-based triage tool in rural clinics.")
add("wearable-sensor","Wearable Multimodal Sensors with Deep Learning","Biomedical-Engineering","Wearable patch integrates accelerometer 3-axis plus minus 16g, gyroscope, ECG, and skin temperature sensors. Deep learning model 1D-CNN plus attention processes multi-channel time series for activity recognition and health monitoring. Activity classification 12 classes walking running sitting standing climbing stairs cycling with 96.5 percent accuracy. ECG analysis R-peak detection 99.2 percent sensitivity arrhythmia classification AFib PVC PAC with 94 percent accuracy. Flexible PCB on polyimide substrate thickness 0.3mm. Battery life 72 hours continuous recording. BLE 5.0 transmission.")
add("eeg-implant","Intracranial EEG Brain-Computer Interface Implant","Biomedical-Engineering","Implantable intracranial EEG iEEG system with 256-channel micro-electrocorticography array. Electrode diameter 50 micrometer platinum-iridium with PEDOT PSS coating for impedance reduction from 1 Megaohm to 50 kiloohm at 1 kHz. Subdural placement on motor cortex. Wireless power transfer via inductive coupling at 13.56 MHz. Data transmission 24 Mbps via ultra-wideband UWB radio. Neural decoding Kalman filter for continuous cursor control achieving 0.85 correlation with intended trajectory. LFP power in high-gamma band 70 to 150 Hz most informative for motor intention.")
add("tissue-engineering","Bacterial Cellulose for Bone Tissue Engineering","Biomedical-Engineering","Bacterial cellulose BC from Acetobacter xylinum as scaffold for bone tissue regeneration. BC membranes thickness 2 to 5mm with nanofibril network diameter 20 to 100nm mimic extracellular matrix. Mineralization via simulated body fluid SBF immersion deposits hydroxyapatite HA crystals on BC surface. HA BC composite 70 percent porosity compressive modulus 150 MPa comparable to trabecular bone. In vitro MC3T3-E1 pre-osteoblast cells show 4x proliferation increase vs pure BC after 14 days. In vivo rat calvarial defect model 85 percent bone regeneration at 12 weeks. BMP-2 growth factor loading enhances osteoinduction.")
add("drug-delivery","Stimuli-Responsive Hydrogels for Drug Delivery","Biomedical-Engineering","Smart hydrogels respond to pH temperature enzymes or light for on-demand drug release. PNIPAAm-based thermoresponsive hydrogel undergoes volume phase transition at 32 Celsius LCST. pH-responsive poly acrylic acid swells at pH over 5.5 intestinal releasing drug selectively. Glucose-responsive phenylboronic acid-modified hydrogel with GOx enzyme for insulin delivery. Drug loading 15 to 30 weight percent via in-situ polymerization. Core-shell nanoparticle-hydrogel hybrids for multi-drug sequential release. In vivo mouse tumor model DOX-loaded hydrogel reduces tumor volume 80 percent at day 21 versus 30 percent for free DOX.")

add("vla-robot","Vision-Language-Action Models for Robot Manipulation","Embodied-AI","RT-2 Robotics Transformer 2 uses vision-language model PaLI-X PaLM-E with action tokens for closed-loop robot control. Co-fine-tuned on internet-scale vision-language data and robot trajectory data. Input camera image plus text instruction. Output discretized action tokens arm position delta gripper state. 6-DoF end-effector actions discretized into 256 bins per dimension. Training data 130k robot demonstrations across 13 tasks from 7 robot embodiments. Generalization 2x improvement over RT-1 on unseen objects and backgrounds. Emergent capabilities symbolic reasoning multi-step planning. Latency 200ms per action step on TPUv4.")
add("sim2real","Sim-to-Real Transfer for Legged Locomotion","Embodied-AI","Domain randomization enables zero-shot sim-to-real transfer of legged locomotion policies. Training 4096 parallel environments in Isaac Gym with randomized dynamics mass plus minus 20 percent friction 0.3 to 1.5 joint damping motor strength. Observations joint positions velocities base orientation gravity vector previous actions height scan. Actions target joint positions at 50 Hz. PPO training 20k iterations batch size 98k. Deployment on Unitree A1 quadruped walks at 0.8 m per second on grass gravel slopes 15 degrees stairs. Recovery from external pushes 50N. Latent space adaptation 50 online iterations adapt to new terrain within 5 seconds.")
add("world-model","World Models for Embodied AI Planning","Embodied-AI","DreamerV3 learns world model from pixels and uses it for behavior learning. World model components RSSM Recurrent State-Space Model with deterministic recurrent state and stochastic discrete latents 32 categorical variables 32 classes each. Trained via reconstruction image reward prediction and continue prediction losses. Actor-critic trained entirely in imagination latent space rollouts. Symlog predictions for reward value continue to handle varying scales. Evaluated on 150 plus tasks across 5 domains DeepMind Control Suite Atari Crafter Minecraft. Minecraft diamond acquisition without human demonstrations. 1M environment steps 100M imagination steps.")
add("humanoid","Humanoid Robot Loco-Manipulation","Embodied-AI","Humanoid robot combines bipedal locomotion with whole-body manipulation. Digit robot Agility Robotics 1.55m tall 42.2kg 20 DoF arms 4x2 legs 6x2. MPC-based walking controller with 2ms control loop. Footstep planning via A-star search with terrain cost map. Arm control operational space control with null-space posture optimization. Coordinated loco-manipulation walking while carrying 10kg box opening doors pushing carts. State estimation IMU plus joint encoders plus foot contact sensors via EKF. Battery 5 kWh Li-ion 4 hours continuous operation.")
add("vla-xr1","XR-1 VLA Large Model for General-Purpose Robots","Embodied-AI","XR-1 integrates vision ViT-L/14 language LLaMA-3 8B and action diffusion policy into unified VLA model. Training two-stage first pre-train vision-language alignment on 100M image-text pairs then fine-tune action head on 50k manipulation trajectories. Diffusion policy 16-step denoising predicts 32 future actions. Action space 7-DoF end-effector pose position delta xyz rotation delta quaternion plus gripper continuous open close. Benchmarks CALVIN ABCD to D split 87 percent success LIBERO 82 percent across 5 task suites. Real robot experiments 15 household tasks pouring wiping sorting pick-place. Failure recovery re-planning when confidence under 0.7. Inference 150ms on A100 GPU.")

add("electrocatalysis","Electrocatalysis for Hydrogen and Oxygen Evolution","Chemistry-Catalysis","Electrocatalysts for HER hydrogen evolution reaction and OER oxygen evolution reaction are central to water splitting. Pt C remains benchmark for HER with overpotential under 50 mV at 10 mA per square centimeter. Transition metal alternatives MoS2 edge sites NiFe LDH for OER with overpotential 250 mV. Bifunctional catalysts for overall water splitting CoP Ni2P Fe-doped Ni OH 2. Tafel slope analysis reveals Volmer-Heyrovsky versus Volmer-Tafel mechanisms. Operando XAS reveals active species formation during catalysis.")
add("ml-catalysis","Machine Learning for Heterogeneous Catalysis","Chemistry-Catalysis","ML interatomic potentials model surface reactions on catalytic nanoparticles. Graph neural networks predict adsorption energies from atomic structure. Training data DFT calculations of adsorbates on transition metal surfaces. Accuracy adsorption energy MAE 0.15 eV versus DFT. Active learning reduces required DFT calculations by 80 percent. Applications CO2 reduction on Cu, NH3 synthesis on Fe, oxygen reduction on Pt alloys. Descriptor-based models d-band center coordination number provide interpretability.")
add("photocatalysis","TiO2 Photocatalysis for Fluoroalkylation","Chemistry-Catalysis","TiO2 photocatalyst enables fluoroalkylation via single electron transfer under UV light. Ligand-to-metal charge transfer generates reactive radical intermediates. Substrate scope aromatic and heteroaromatic compounds. Yield 60 to 90 percent for perfluoroalkylation. Photocatalytic cycle TiO2 absorbs UV generates electron-hole pair oxidizes fluoroalkyl reagent. Continuous flow reactor improves throughput and selectivity. Bandgap engineering via doping extends response to visible light.")
add("polymer-catalysts","Organic Polymer Catalysts for Sustainable Chemistry","Chemistry-Catalysis","Conjugated microporous polymers and covalent organic frameworks as heterogeneous catalysts. High surface area over 1000 square meters per gram. Tunable pore size from 1 to 5 nm. Metal-free organocatalysis amine carbene phosphoric acid functionalities. Metallated variants Pd Ru Ir for cross-coupling hydrogenation. Recyclability over 10 cycles without activity loss. Flow chemistry integration with packed-bed reactors. Photoredox-active polymers for light-driven reactions.")
add("single-atom","Single-Atom Catalysts for Energy Conversion","Chemistry-Catalysis","Single-atom catalysts maximize atom efficiency with 100 percent metal dispersion. Synthesis wet impregnation atomic layer deposition MOF pyrolysis. Support N-doped carbon metal oxides MoS2. M-N4 sites M equals Fe Co Ni Mn for ORR with activity surpassing Pt C in alkaline media. SAC for CO2 reduction Ni-N4 sites produce CO with over 95 percent Faradaic efficiency. Stability under 100 hour operation. Characterization HAADF-STEM confirms atomic dispersion XANES EXAFS reveals coordination environment.")

print(f"Loaded {len(DOCS)} documents across 6 domains")

# ── Tokenize and build BM25 ──
def tokenize(text):
    return re.findall(r'[a-zA-Z0-9]+', text.lower())

corpus = [d["content"] for d in DOCS]
tokenized = [tokenize(c) for c in corpus]
bm25 = BM25Okapi(tokenized)

print(f"BM25 index: {len(tokenized)} docs")

# ── Queries ──
QUERIES = [
    ("Q-AI-1","deep Q-network reinforcement learning Atari games experience replay","AI-ML-Research"),
    ("Q-AI-2","multi-head self-attention scaled dot-product transformer architecture","AI-ML-Research"),
    ("Q-AI-3","SHAP value explainable AI feature importance model interpretation","AI-ML-Research"),
    ("Q-EN-1","battery thermal management phase change material liquid cooling PCM","Energy-Batteries"),
    ("Q-EN-2","solid-state electrolyte lithium ion conductivity sulfide NASICON","Energy-Batteries"),
    ("Q-EN-3","sodium ion battery cathode anode comparison LFP NMC","Energy-Batteries"),
    ("Q-MA-1","MXene Ti3C2Tx supercapacitor specific capacitance interlayer","Materials-Science"),
    ("Q-MA-2","machine learning interatomic potential DFT replacement materials","Materials-Science"),
    ("Q-MA-3","2D materials graphene transition metal dichalcogenide roadmap","Materials-Science"),
    ("Q-BI-1","convolutional neural network medical imaging chest X-ray pneumonia","Biomedical-Engineering"),
    ("Q-BI-2","wearable multimodal sensor motion detection accelerometer deep learning","Biomedical-Engineering"),
    ("Q-BI-3","intracranial EEG brain-computer interface neural recording implantable","Biomedical-Engineering"),
    ("Q-EM-1","humanoid robot loco-manipulation vision-language-action model","Embodied-AI"),
    ("Q-EM-2","Sim-to-Real transfer domain randomization legged locomotion policy","Embodied-AI"),
    ("Q-EM-3","world model embodied AI Dreamer reinforcement learning planning","Embodied-AI"),
    ("Q-CH-1","electrocatalysis hydrogen evolution reaction oxygen evolution overpotential","Chemistry-Catalysis"),
    ("Q-CH-2","heterogeneous catalysis machine learning potential surface reaction barrier","Chemistry-Catalysis"),
    ("Q-CH-3","photocatalysis TiO2 fluoroalkylation ligand metal charge transfer","Chemistry-Catalysis"),
    ("Q-AD-1","reinforcement learning optimization policy gradient materials design",""),
    ("Q-AD-2","deep learning CNN lightweight efficient model edge deployment",""),
    ("Q-AD-3","graph neural network state estimation prediction time series",""),
    ("Q-AD-4","thermal management cooling heat transfer computational fluid dynamics",""),
    ("Q-AD-5","machine learning healthcare diagnosis classification detection",""),
    ("Q-AD-6","neural network membrane design polymer electrolyte inverse optimization",""),
    ("Q-AD-7","attention mechanism robot control manipulation planning vision",""),
    ("Q-AD-8","catalyst design screening high-throughput computational prediction",""),
    ("Q-AM-1","transformer architecture natural language processing",""),
    ("Q-AM-2","energy storage battery materials electrolyte electrode design",""),
    ("Q-AM-3","sensor detection monitoring real-time wearable biomedical",""),
    ("Q-AM-4","machine learning model training optimization gradient descent",""),
]

# ── Run ──
all_results = []
p1_correct = p3_correct = p5_correct = 0
domain_specific_count = 0

for i, (qid, query, expected_domain) in enumerate(QUERIES):
    q_tokens = tokenize(query)
    scores = bm25.get_scores(q_tokens)
    ranked = sorted(enumerate(scores), key=lambda x: -x[1])
    top5 = ranked[:5]
    
    results = []
    for rank, (idx, score) in enumerate(top5):
        doc = DOCS[idx]
        results.append({
            "rank": rank+1, "doc_id": doc["id"], "title": doc["title"],
            "domain": doc["domain"], "score": round(float(score), 4)
        })
    
    # Check correctness for domain-specific queries
    correct_hits = 0
    if expected_domain:
        domain_specific_count += 1
        for j, r in enumerate(results):
            if r["domain"] == expected_domain:
                correct_hits += 1
                if j == 0: p1_correct += 1
                if j < 3: p3_correct += 1
        if correct_hits > 0: p5_correct += 1
    
    all_results.append({"qid":qid,"query":query,"expected_domain":expected_domain,"results":results})
    print(f"[{i+1:2d}/30] {qid}: top-1={results[0]['doc_id']} ({results[0]['domain']}) score={results[0]['score']:.4f}")

# ── Compute metrics ──
print(f"\n{'='*60}")
print(f"BM25 RESULTS")
print(f"{'='*60}")
print(f"P@1  = {p1_correct}/{domain_specific_count} = {p1_correct/domain_specific_count*100:.1f}%")
print(f"P@3  = {p3_correct}/{domain_specific_count*3} = {p3_correct/(domain_specific_count*3)*100:.1f}%") 
print(f"P@5  = {p5_correct}/{domain_specific_count} = {p5_correct/domain_specific_count*100:.1f}%")

# MRR
mrr = 0
for r in all_results:
    if not r["expected_domain"]: continue
    for j, res in enumerate(r["results"]):
        if res["domain"] == r["expected_domain"]:
            mrr += 1/(j+1)
            break
mrr = mrr / domain_specific_count if domain_specific_count else 0
print(f"MRR  = {mrr:.4f}")

# Domain distribution for adversarial queries
print(f"\nAdversarial queries domain distribution:")
for r in all_results:
    if not r["expected_domain"]:
        domains = {}
        for res in r["results"][:3]:
            domains[res["domain"]] = domains.get(res["domain"],0) + 1
        print(f"  {r['qid']}: top-3 domains = {domains}")

# ── Save ──
with open("results/aggregate.json","w") as f:
    json.dump({
        "method": "BM25",
        "total_queries": len(all_results),
        "domain_specific": domain_specific_count,
        "p_at_1": p1_correct/domain_specific_count,
        "p_at_3": p3_correct/(domain_specific_count*3),
        "p_at_5": p5_correct/domain_specific_count,
        "mrr": mrr,
    }, f, indent=2)

with open("results/raw/all_queries.json","w") as f:
    json.dump(all_results, f, indent=2)

print(f"\nResults saved to results/")
