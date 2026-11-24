"""Regenerate ``external-baselines-qa.tex`` from the shipped experiment records.

The transcript prints every answer of the unified eight-arm comparison
(eight arms x BQ01--BQ10) with its judge scores and rationale, preceded by the
verbatim prompt texts. Inputs are the files shipped next to this script:

    experiment_data/external_baselines_v3/answers-v3.jsonl
    experiment_data/external_baselines_v3/judgments-unified.jsonl
    experiment_data/external_baselines_v3/protocol/answer-prompt.txt
    experiment_data/external_baselines_v3/protocol/judge-instruction.txt

Run from any directory with ``python build_external_baselines_qa.py``; the
output is written next to this script. Compile it with
``latexmk -pdf external-baselines-qa.tex``.

The raw records are never modified. Three display rules keep the transcript
consistent with the manuscript's wording:

* a model identifier is shown without its provider prefix
  (``<provider>/deepseek-flash`` becomes ``deepseek-flash``);
* the native DeepRead provenance note, whose model identifier conflicts with
  the row's generator field, is replaced by a neutral label. The conflict is
  reported in the manuscript's threats section; the original string remains
  in ``answers-v3.jsonl``;
* the metered cost of the native DeepRead arm is shown as not recorded, as in
  Table 5 of the manuscript (its pipeline does not meter calls through the
  shared endpoint).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "experiment_data" / "external_baselines_v3"
ANSWERS = DATA / "answers-v3.jsonl"
JUDGMENTS = DATA / "judgments-unified.jsonl"
PROTOCOL = DATA / "protocol"
OUT = ROOT / "external-baselines-qa.tex"

ARMS = ["hmrs-agent", "bm25", "dense", "rrf", "raptor", "lightrag",
        "deepread-native", "graphrag"]
LABELS = {
    "hmrs-agent": "HMRS agent (pinned)",
    "bm25": "BM25 baseline",
    "dense": "Dense BGE-M3 baseline",
    "rrf": "RRF baseline",
    "raptor": "RAPTOR tree retrieval",
    "lightrag": "LightRAG mixed retrieval",
    "deepread-native": "DeepRead native pipeline",
    "graphrag": "GraphRAG local search",
}
DEEPREAD_NOTE = "native DeepRead agent pipeline (disclosed)"
# The reconstructed prompt instance shown in the protocol section.
EXAMPLE_ARM, EXAMPLE_QID = "dense", "BQ01"

DIMENSIONS = ["factual", "completeness", "groundedness", "sources"]


def ascii_safe(x: object) -> str:
    x = str(x or "").replace("\r", "").replace("\x00", "")
    x = x.replace("\\end{Verbatim}", "[end-Verbatim token omitted]")
    return x.encode("ascii", "backslashreplace").decode("ascii")


def latex_escape(x: object) -> str:
    x = ascii_safe(x)
    return (x.replace("\\", "\\textbackslash{}").replace("&", "\\&")
            .replace("%", "\\%").replace("#", "\\#").replace("_", "\\_")
            .replace("{", "\\{").replace("}", "\\}"))


def display_model(model: object) -> str:
    """Model identifier without its provider prefix."""
    return str(model or "").rsplit("/", 1)[-1]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()
            if x.strip()]


def protocol_section(by: dict) -> list[str]:
    """Verbatim prompt texts, placed before the per-arm sections."""
    template = (PROTOCOL / "answer-prompt.txt").read_text(encoding="utf-8").rstrip("\n")
    judge = (PROTOCOL / "judge-instruction.txt").read_text(encoding="utf-8").rstrip("\n")
    head = template.split("\n\nQuestion:")[0]
    example = by[(EXAMPLE_ARM, EXAMPLE_QID)]
    units = example.get("sources") or []
    context = "\n\n".join(
        f"[S{n}] {u['doc_path']}\n{u['text']}" for n, u in enumerate(units, 1))
    instance = (head + f"\n\nQuestion: {example.get('question', '')}\n\nContext:\n"
                + context + "\n\nAnswer:")
    lines = [
        r"\section*{Protocol texts}",
        r"\addcontentsline{toc}{section}{Protocol texts}",
        r"\subsection*{Answer prompt of the retrieval-mode arms}",
        "The six retrieval-mode arms (BM25, dense, RRF, RAPTOR, LightRAG and "
        "GraphRAG) received one prompt per question, built from the template "
        "below; angle brackets mark the text substituted per question. The "
        "HMRS agent and the native DeepRead pipeline ran their own multi-turn "
        "procedures and did not use this prompt.",
        r"\begin{EvidenceText}",
        template,
        r"\end{EvidenceText}",
        "The prompt below reconstructs the dense answer to "
        f"{EXAMPLE_QID} from its {len(units)} recorded context units "
        r"(\path{sources} in \path{answers-v3.jsonl}).",
        r"\begin{EvidenceText}",
        ascii_safe(instance),
        r"\end{EvidenceText}",
        r"\clearpage",
        r"\subsection*{Judge instruction of the unified batch}",
        "Every judge packet began with the instruction below, identical for "
        "all ten questions, followed by the question, a head-only excerpt of "
        "the gold paper and the eight anonymised answers in a fresh random "
        r"letter order (\path{mapping-unified.json}). The fourth dimension is "
        "called attribution in the manuscript.",
        r"\begin{EvidenceText}",
        judge,
        r"\end{EvidenceText}",
    ]
    return lines


def main() -> None:
    answers = load_jsonl(ANSWERS)
    judgments = load_jsonl(JUDGMENTS)
    by = {(r["arm"], r["qid"]): r for r in answers}
    jby = {(r["arm"], r["qid"]): r for r in judgments}
    assert len(by) == 80 and len(jby) == 80, "expected 8 arms x 10 questions"
    assert (ANSWERS.parent / "mapping-unified.json").exists()
    qids = sorted({r["qid"] for r in answers})

    lines = [
        r"\documentclass[10pt]{article}",
        r"\usepackage[a4paper,margin=0.75in]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{fvextra}",
        r"\usepackage{longtable}",
        r"\usepackage{booktabs}",
        r"\usepackage{xcolor}",
        r"\usepackage{hyperref}",
        r"\usepackage{microtype}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{4pt}",
        r"\DefineVerbatimEnvironment{AnswerText}{Verbatim}{fontsize=\scriptsize,breaklines=true,breakanywhere=true,frame=single,framesep=3pt}",
        r"\DefineVerbatimEnvironment{EvidenceText}{Verbatim}{fontsize=\tiny,breaklines=true,breakanywhere=true,frame=single,framesep=2pt}",
        r"\begin{document}",
        r"\begin{center}{\Large\bfseries External-baseline answer and evidence audit}\\[4pt]{\normalsize Unified batch: 8 arms $\times$ 10 questions = 80 answers}\end{center}",
        r"\textbf{Purpose.} This companion appendix preserves the complete answer text and retrieval provenance for the external-baseline batch. It is an audit transcript, not an additional statistical analysis. The raw JSONL files in \path{experiment_data/external_baselines_v3/} are the exact machine-readable source; Unicode source paths are rendered with ASCII escapes in this PDF where necessary. Model identifiers are shown without their provider prefix.",
        "",
        r"\textbf{Judging.} Each entry reports the four dimension scores, the verdict, the overall arithmetic mean and the judge's rationale. For each question the judge saw the eight anonymised answers of this batch together with a head-only excerpt of the gold paper, never the retrieved context or a system name. The scores are reported in Table 5 of the main text and Supplementary Tables S19--S20; the earlier passes, corpus scopes and pipeline limitations are reported in Supplementary Tables S19--S21.",
        "",
        r"\tableofcontents",
        r"\clearpage",
    ]
    lines += protocol_section(by)
    for arm in ARMS:
        lines.append(f"\\section{{{LABELS[arm]}}}")
        for qid in qids:
            a = by[(arm, qid)]
            j = jby[(arm, qid)]
            overall = sum(j[k] for k in DIMENSIONS) / 4
            cost = ("not recorded" if arm == "deepread-native"
                    else f"{a.get('cost_usd')} USD")
            lines.append(f"\\subsection{{{qid}: {latex_escape(a.get('question', ''))}}}")
            lines.append(r"\begin{tabular}{@{}ll@{}}")
            lines.append("Arm & " + latex_escape(LABELS[arm]) + r"\\")
            lines.append("Generator & "
                         + latex_escape(f"{a.get('engine')} / {display_model(a.get('model'))}")
                         + r"\\")
            lines.append("HTTP / success & "
                         + latex_escape(f"{a.get('http')} / {a.get('success')}") + r"\\")
            lines.append("Wall time / cost & "
                         + latex_escape(f"{a.get('wall_s')} s / {cost}") + r"\\")
            lines.append("Judge scores & "
                         + latex_escape(f"F={j['factual']}, C={j['completeness']}, "
                                        f"G={j['groundedness']}, A={j['sources']}; "
                                        f"overall={overall:.2f}") + r"\\")
            lines.append("Verdict & " + latex_escape(j["verdict"]) + r"\\")
            lines.append(r"\end{tabular}")
            lines.append("")
            meta = a.get("index_meta") or {}
            if meta:
                shown = dict(meta)
                if "generator_disclosure" in shown:
                    shown["generator_disclosure"] = DEEPREAD_NOTE
                lines.append(r"\textbf{Index/retrieval metadata}")
                lines.append(r"\begin{EvidenceText}")
                lines.append(ascii_safe(json.dumps(shown, ensure_ascii=False, indent=2)))
                lines.append(r"\end{EvidenceText}")
                lines.append("")
            lines.append(r"\textbf{Dimension rationale}")
            lines.append(r"\begin{EvidenceText}")
            lines.append(ascii_safe(json.dumps(j.get("dim_rationale", {}), ensure_ascii=False, indent=2)))
            lines.append(r"\end{EvidenceText}")
            lines.append("")
            lines.append(r"\textbf{Judge summary}")
            lines.append(r"\begin{EvidenceText}")
            lines.append(ascii_safe(j.get("rationale", "")))
            lines.append(r"\end{EvidenceText}")
            lines.append("")
            lines.append(r"\textbf{Complete answer}")
            lines.append(r"\begin{AnswerText}")
            lines.append(ascii_safe(a.get("answer", "")))
            lines.append(r"\end{AnswerText}")
            lines.append("")
            lines.append(r"\textbf{Retrieved evidence index (all returned units; paths and scores) }")
            lines.append(r"\begin{EvidenceText}")
            for idx, src in enumerate(a.get("sources") or [], 1):
                lines.append(ascii_safe(f"[{idx}] score={src.get('score')} path={src.get('doc_path')}"))
            if not a.get("sources"):
                lines.append("[No source list recorded for this arm.]")
            lines.append(r"\end{EvidenceText}")
    lines.append(r"\end{document}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(OUT, "lines", len(lines), "bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
