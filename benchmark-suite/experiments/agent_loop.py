"""Generic tool-using agent loop (LLM = omp oneshot, one process per step).

The agent sees a tool catalog + running transcript and must reply with exactly one
JSON object per step:  {"tool": "<name>", "args": {...}}  or  {"final": "<answer>"}.
Tool observations are appended to the transcript (truncated to keep prompts bounded).
"""
from __future__ import annotations

import json
import re
import time

from algorithms.omp_client import OmpOneshot, extract_json

OBS_CHARS = 2600          # per-observation cap inside the transcript
FINAL_RETRY = "Your last reply was not a single valid JSON object. Reply again with ONLY one JSON object: {\"tool\": ..., \"args\": {...}} or {\"final\": \"...\"}"


class Tool:
    def __init__(self, name: str, desc: str, args: dict, fn):
        self.name, self.desc, self.args, self.fn = name, desc, args, fn

    def spec(self) -> str:
        params = ", ".join(f"{k}:{v}" for k, v in self.args.items())
        return f"- {self.name}({params}): {self.desc}"


class ToolAgent:
    def __init__(self, track: str, system: str, tools: list, stage: str,
                 max_steps: int = 8, llm_timeout: float = 240.0,
                 require_evidence: bool = True):
        self.track = track
        self.system = system
        self.tools = {t.name: t for t in tools}
        self.max_steps = max_steps
        self.require_evidence = require_evidence
        self.llm = OmpOneshot(stage=stage, timeout=llm_timeout)
        self.log: list[dict] = []

    def _catalog(self) -> str:
        return "\n".join(t.spec() for t in self.tools.values())

    def _step_prompt(self, question: str, transcript: str, note: str = "") -> str:
        return f"""{self.system}

QUESTION: {question}

AVAILABLE TOOLS:
{self._catalog()}

TRANSCRIPT SO FAR:
{transcript or '(empty — this is your first step)'}

{note}Reply with ONLY one JSON object, nothing else:
{{"tool": "<tool name>", "args": {{"<arg>": <value>, ...}}}}   ← to call exactly one tool
{{"final": "<your complete answer>"}}                          ← when you can answer"""

    def run(self, question: str) -> dict:
        t0 = time.perf_counter()
        transcript, note = "", ""
        answer, steps, ok_tools = "", [], 0
        for step in range(1, self.max_steps + 1):
            t_llm = time.perf_counter()
            raw = self.llm(self._step_prompt(question, transcript, note),
                           system="You are a precise retrieval agent. Output only JSON.")
            llm_s = round(time.perf_counter() - t_llm, 1)
            parsed = extract_json(raw)
            if not isinstance(parsed, dict) or ("tool" not in parsed and "final" not in parsed):
                if step == self.max_steps:
                    answer, steps = raw.strip()[:2000], steps
                    self.log.append({"step": step, "force_final_raw": True})
                    break
                note = FINAL_RETRY + "\n\n"
                self.log.append({"step": step, "parse_error": raw[:200]})
                continue
            note = ""
            if "final" in parsed:
                if self.require_evidence and ok_tools == 0:
                    # Evidence floor: an answer without any executed retrieval
                    # tool call would be parametric knowledge, not retrieval.
                    self.log.append({"step": step,
                                     "rejected_final_no_evidence": True})
                    note = ("EVIDENCE POLICY VIOLATION: you answered without "
                            "executing any tool. This experiment requires you to "
                            "retrieve first. Call your retrieval tool now, read "
                            "the observation, and only then answer.\n\n")
                    continue
                answer = str(parsed["final"]).strip()
                self.log.append({"step": step, "final": True, "llm_s": llm_s})
                break
            tname, args = parsed.get("tool"), parsed.get("args") or {}
            tool = self.tools.get(str(tname))
            if tool is None:
                obs = {"error": f"unknown tool {tname!r}", "available": list(self.tools)}
            else:
                t_tool = time.perf_counter()
                try:
                    obs = tool.fn(**{k: v for k, v in args.items() if k in tool.args})
                    ok_tools += 1
                except Exception as e:  # noqa: BLE001 — observation, not crash
                    obs = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
                tool_s = round(time.perf_counter() - t_tool, 1)
                self.log.append({"step": step, "tool": tname, "args": args,
                                 "tool_s": tool_s, "llm_s": llm_s})
                steps.append({"step": step, "tool": tname, "args": args,
                              "tool_s": tool_s})
            obs_text = json.dumps(obs, ensure_ascii=False)[:OBS_CHARS]
            transcript += f"\n[step {step}] you called {tname}({json.dumps(args, ensure_ascii=False)})\nobservation: {obs_text}\n"
        else:
            answer = "(max steps reached without a final answer)"
        return {"track": self.track, "answer": answer, "steps": steps,
                "seconds": round(time.perf_counter() - t0, 1),
                "tool_calls": len(steps), "evidence_enforced": self.require_evidence,
                "agent_log": self.log}
