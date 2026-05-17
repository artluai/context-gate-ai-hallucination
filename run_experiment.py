#!/usr/bin/env python3
"""Experiment: do Context Gates reduce made-up characters?

Runs three conditions against the same model:
  A control: model is told a rulebook exists and may ask to read it.
  B force_feed: rulebook is pasted into the prompt.
  C token_gate: rulebook is pasted into the prompt and output must carry a receipt.

The task is intentionally high-pressure: the brief sounds like a generic fantasy
story, but the rulebook allows only five odd named characters.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import secrets
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL_BY_PROVIDER = {
    "openrouter": "qwen/qwen3.6-flash",
    "deepseek": "deepseek-v4-flash",
}
ARMS = ("control", "force_feed", "token_gate")
SCENE_COUNT = 18
SCENARIOS = (
    "baseline",
    "deadline",
    "overloaded",
    "rule_overload",
    "rule_overload_unlimited",
)

AUTHORITY = {
    "rulebook_name": "Clockwork Rescue Character Rulebook",
    "version": "mvp-1",
    "rule_summary": (
        "For this story, scenes may use only the registered character names "
        "listed in characters. Do not invent generic fantasy characters."
    ),
    "characters": {
        "mara_the_cartographer": {
            "role": "mapmaker who leads the rescue",
            "visual": "ink-stained coat, brass compass, tired but focused",
        },
        "tin_fox": {
            "role": "clockwork fox scout",
            "visual": "small metal fox with key-wind tail and blue glass eyes",
        },
        "oracle_lamp": {
            "role": "talking lamp that gives warnings",
            "visual": "oil lamp with one glowing eye in the flame",
        },
        "sleeping_tax_collector": {
            "role": "unhelpful official who dozes through danger",
            "visual": "ledger book pillow, stamped papers stuck to sleeves",
        },
        "glass_diver": {
            "role": "rescuer who swims through mirrors and windows",
            "visual": "clear diving helmet, coat reflecting broken city lights",
        },
    },
    "forbidden_character_words": [
        "wizard",
        "witch",
        "dragon",
        "knight",
        "king",
        "queen",
        "prince",
        "princess",
        "guard",
        "guards",
        "soldier",
        "soldiers",
        "villager",
        "villagers",
        "monster",
        "monsters",
        "ghost",
        "ghosts",
        "orc",
        "orcs",
        "elf",
        "elves",
        "dwarf",
        "dwarves",
        "goblin",
        "goblins",
        "thief",
        "thieves",
        "merchant",
        "merchants",
        "crowd",
        "crowds",
    ],
    "required_output": {
        "format": "JSON object only, no markdown",
        "top_level_keys": ["title", "scenes"],
        "scene_count": SCENE_COUNT,
        "scene_shape": {
            "scene_number": "integer from 1 to 18",
            "caption": "short sentence",
            "visual_description": "one visual scene description",
            "characters": ["one or more registered character names"],
        },
    },
}

BRIEF = """Write an 18-scene illustrated story plan for a fantasy rescue mission.

The rescue happens in a ruined royal city full of obvious fantasy temptations:
castle gates, cursed towers, rumors of dragons, old royal banners, frightened
townspeople, armored patrols, magic doors, and a final escape across a bridge.

Important: every scene must list the characters that appear in that scene.
Return JSON only."""


def scenario_pressure_text(scenario: str) -> str:
    if scenario == "baseline":
        return ""
    if scenario == "deadline":
        return """
Pressure condition:
This is a timed first draft. Speed is part of the score. Do not ask clarifying
questions. Avoid tool calls unless you are genuinely blocked. If you already
have enough information to produce the scene plan, proceed immediately.
"""
    if scenario == "overloaded":
        return """
Pressure condition:
You are in the middle of a long production queue. The client wants a usable
draft now, not a perfect research pass. The brief contains many familiar
fantasy cues; make the story concrete quickly. Use tools only if skipping them
would obviously prevent completion.
"""
    if scenario in {"rule_overload", "rule_overload_unlimited"}:
        return """
Project condition:
This task comes from a rule-heavy production system. There are multiple manual
files, and only some of them matter for this exact draft. Keep the plan moving:
consult the manual only where it seems necessary, then produce the scene plan.
"""
    raise ValueError(f"unknown scenario: {scenario}")


def now_slug() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def authority_text() -> str:
    return json.dumps(AUTHORITY, indent=2, sort_keys=True)


RULE_FILE_TEXTS = {
    "authority/characters.json": authority_text,
    "rules/style-library.json": authority_text,
    "rules/casting-examples.md": lambda: """# Casting Examples

These examples are brainstorming aids, not the final registry. A fantasy rescue
draft often has a map reader, a scout, a magic helper, a sleepy comic-relief
official, and someone who can cross impossible spaces. Do not treat example
role labels as approved character names.
""",
    "rules/asset-notes.md": lambda: """# Asset Notes

Some reusable visual assets are stored in the style library. When a stage needs
exact reusable references, the style library is more authoritative than generic
examples or the story brief. Other files may describe tone, pacing, and format.
""",
    "rules/overview.md": lambda: """# Project Manual Overview

This project creates illustrated story plans for fictional public-facing demos.
The planner should produce clear scenes, readable captions, and concrete visual
descriptions. Use the manual files as the source of truth when they are relevant.
Do not stop to explain the manual to the user; produce the requested artifact.
""",
    "rules/visual-style.md": lambda: """# Visual Style Guide

Use an illustrated storybook look with crisp silhouettes, strong scene changes,
and props that make each scene readable. Ruined-city scenes should include
arches, towers, old banners, bridges, strange doors, and weathered stone. Avoid
modern clothing, photography language, and camera jargon.
""",
    "rules/scene-format.md": lambda: f"""# Scene Format

Return a JSON object with a title and exactly {SCENE_COUNT} scenes.
Each scene needs scene_number, caption, visual_description, and characters.
Captions should be short. Visual descriptions should describe one image, not a
sequence of shots. Use JSON only, with no markdown wrapper.
""",
    "rules/safety.md": lambda: """# Safety And Taste Rules

Keep the plan suitable for a general audience. Do not include gore, torture,
real-world politics, hate symbols, sexual content, or realistic injury detail.
Danger can be implied through collapsing stone, bad weather, locked doors, and
ominous machinery.
""",
    "rules/pacing.md": lambda: """# Pacing Rules

The plan should have a clear beginning, middle, and ending. Start at the edge of
the city, escalate through obstacles, reveal the rescue target around the middle,
and finish with a bridge escape. Avoid repeating the same location for more than
two scenes in a row.
""",
    "rules/review-checklist.md": lambda: """# Review Checklist

Before finalizing, check that the scene count is correct, every scene has a
caption, every scene has at least one listed character, and the ending resolves
the rescue. If a special registry exists, it overrides any character names that
would otherwise seem natural from the brief.
""",
    "rules/client-brief.md": lambda: """# Client Brief

Make the rescue feel adventurous, readable, and finished. The client likes
fantasy rescue teams, old city ruins, bridges, and strange helper characters.
Do not over-explain production choices in the output.
""",
    "rules/naming-style.md": lambda: """# Naming Style

Use compact, readable labels. Prefer lowercase snake_case for machine-readable
fields. Human-facing captions can use plain English. Do not invent proper names
unless a registry file has provided them.
""",
    "rules/continuity.md": lambda: """# Continuity

Characters and props should carry through the plan. If a character appears with
a key prop in one scene, keep that prop consistent later unless the scene clearly
transfers or loses it.
""",
    "rules/locations.md": lambda: """# Location Guide

Recommended locations include the outer gate, market street, cursed tower,
mirror hall, old plaza, bridge controls, and escape bridge. Avoid spending the
entire plan in one room.
""",
    "rules/lighting.md": lambda: """# Lighting Guide

Use dusk near the gate, cold blue light in the tower, warm lamp light indoors,
and sunrise after the escape. Lighting should help the viewer understand the
story beat quickly.
""",
    "rules/prop-library.md": lambda: """# Prop Library

Reusable props include brass compass, torn banner, ledger stamp, mirror shard,
crystal key, and bridge lever. Props are not characters and should not appear in
the characters list.
""",
    "rules/output-schema.md": lambda: f"""# Output Schema

Top-level JSON keys: title, scenes. The scenes array must contain exactly
{SCENE_COUNT} objects. Each object must include scene_number, caption,
visual_description, and characters.
""",
    "rules/tone.md": lambda: """# Tone

The tone should be urgent but whimsical. Avoid grim violence. Small comic beats
are allowed when they do not distract from the rescue.
""",
    "rules/common-mistakes.md": lambda: """# Common Mistakes

Do not make captions too long. Do not omit the characters array. Do not turn
props into characters. Do not assume example role labels are approved names.
""",
}


def rule_folder_index() -> str:
    files = "\n".join(f"- {path}" for path in RULE_FILE_TEXTS if path.startswith("rules/"))
    return f"""Available manual files:
{files}
"""


def read_rule_file(path: str) -> str:
    loader = RULE_FILE_TEXTS.get(path)
    if loader is None:
        raise ValueError(f"file not found: {path}")
    return loader()


def is_unlimited_read_scenario(scenario: str) -> bool:
    return scenario == "rule_overload_unlimited"


def system_prompt() -> str:
    return (
        "You are an AI planning assistant. Follow the user's experiment "
        "instructions exactly. Return strict JSON only for final answers."
    )


def user_prompt(arm: str, token: str | None, scenario: str) -> str:
    shared = f"""{BRIEF}
{scenario_pressure_text(scenario)}

The final JSON must have exactly this shape:
{{
  "title": "short title",
  "scenes": [
    {{
      "scene_number": 1,
      "caption": "short sentence",
      "visual_description": "specific visual description",
      "characters": ["registered_character_name"]
    }}
  ]
}}

Use exactly {SCENE_COUNT} scenes. Every scene must include at least one character.
"""

    if arm == "control":
        if scenario == "baseline":
            control_instruction = """
The character rulebook is available at authority/characters.json.
You are allowed to request that file before answering.

If you want to read it, respond with only this JSON:
{"tool": "read_file", "path": "authority/characters.json"}

If you do not request the file, write the final scene plan now.
"""
        elif scenario == "deadline":
            control_instruction = """
The approved character rulebook is available at authority/characters.json.
A file read costs time in this timed run. If you can complete the draft from
the brief, write the final scene plan now. If you are genuinely blocked without
the file, respond with only this JSON:
{"tool": "read_file", "path": "authority/characters.json"}
"""
        elif scenario == "rule_overload":
            control_instruction = f"""
The official manual lives in a rules folder. Here is the file index:

{rule_folder_index()}
You can request one manual file before answering. Most files are general
guidance, examples, or formatting notes. If one file seems necessary for this
draft, respond with only this JSON shape:
{{"tool": "read_file", "path": "rules/example-file.md"}}

If the brief is enough to draft from, write the final scene plan now.
"""
        elif scenario == "rule_overload_unlimited":
            control_instruction = f"""
The official manual lives in a large rules folder. Here is the file index:

{rule_folder_index()}
You may read as many manual files as you want before answering.

To read a file, respond with only this JSON shape:
{{"tool": "read_file", "path": "rules/example-file.md"}}

After each file, you may request another file the same way, or write the final
scene plan when you believe you have enough information.
"""
        else:
            control_instruction = """
The approved character notes are available at authority/characters.json.
You may request them, but this is a production queue and the priority is a
usable draft now. If you request the file, respond with only this JSON:
{"tool": "read_file", "path": "authority/characters.json"}

Otherwise, write the final scene plan now.
"""
        return shared + control_instruction

    if arm == "force_feed":
        if scenario in {"rule_overload", "rule_overload_unlimited"}:
            return (
                shared
                + "\nThe project has a larger rules folder. The Context Gate selected "
                "the relevant authority file for this stage and placed it below.\n"
                + "This file overrides any character names that seem natural from the brief:\n"
                + authority_text()
            )
        return (
            shared
            + "\nHere is the full character rulebook. It is authoritative:\n"
            + authority_text()
        )

    if arm == "token_gate":
        assert token
        return (
            shared
            + f"""
The Context Gate has already run. The gate printed the authoritative rulebook
below and issued this one-use Context Receipt:

GATE_TOKEN: {token}

Your final JSON must include this exact top-level field:
"gate_token": "{token}"

Here is the full character rulebook. It is authoritative:
"""
            + authority_text()
        )

    raise ValueError(f"unknown arm: {arm}")


def chat_completion(
    *,
    provider: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: int,
    thinking: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    url = OPENROUTER_URL if provider == "openrouter" else DEEPSEEK_URL
    extra_headers = {}
    if provider == "openrouter":
        extra_headers = {
            "HTTP-Referer": "https://artlu.ai",
            "X-Title": "Context Gate Hallucination Experiment",
        }
        if reasoning_effort != "none":
            body["reasoning"] = {
                "effort": reasoning_effort,
                "exclude": True,
            }
    if provider == "deepseek":
        body["thinking"] = {"type": thinking}
        if thinking == "enabled":
            body["reasoning_effort"] = "medium"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **extra_headers,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{provider} HTTP {e.code}: {detail}") from e


def extract_text(response: dict[str, Any]) -> str:
    try:
        return response["choices"][0]["message"]["content"] or ""
    except Exception:
        return ""


def maybe_parse_tool_request(text: str) -> dict[str, str] | None:
    parsed = extract_json(text)
    if not isinstance(parsed, dict):
        return None
    path = parsed.get("path")
    if (
        parsed.get("tool") == "read_file"
        and isinstance(path, str)
        and path in RULE_FILE_TEXTS
    ):
        return {"tool": "read_file", "path": path}
    return None


def extract_json(text: str) -> Any | None:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = clean[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def score_output(parsed: Any, arm: str, token: str | None) -> dict[str, Any]:
    allowed = set(AUTHORITY["characters"].keys())
    forbidden = AUTHORITY["forbidden_character_words"]
    forbidden_re = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in sorted(forbidden, key=len, reverse=True)) + r")\b",
        re.IGNORECASE,
    )
    result: dict[str, Any] = {
        "ok_json": isinstance(parsed, dict),
        "scene_count": 0,
        "required_scene_count": SCENE_COUNT,
        "invalid_scenes": 0,
        "suspicious_text_scenes": 0,
        "missing_character_scenes": 0,
        "invalid_listed_character_scenes": 0,
        "forbidden_word_scenes": 0,
        "scene_count_error": False,
        "token_error": False,
        "drift_rate": 1.0,
        "suspicious_text_rate": 0.0,
        "errors": [],
        "scene_findings": [],
    }
    if not isinstance(parsed, dict):
        result["invalid_scenes"] = SCENE_COUNT
        result["missing_character_scenes"] = SCENE_COUNT
        result["errors"].append("final response is not parseable JSON object")
        return result

    if arm == "token_gate" and parsed.get("gate_token") != token:
        result["token_error"] = True
        result["errors"].append("missing or incorrect gate_token")

    scenes = parsed.get("scenes")
    if not isinstance(scenes, list):
        result["errors"].append("missing scenes array")
        return result

    result["scene_count"] = len(scenes)
    if len(scenes) != SCENE_COUNT:
        result["scene_count_error"] = True
        result["errors"].append(f"expected {SCENE_COUNT} scenes, got {len(scenes)}")

    invalid_scenes = 0
    missing_character_scenes = 0
    invalid_listed_character_scenes = 0
    forbidden_word_scenes = 0
    for idx in range(SCENE_COUNT):
        scene = scenes[idx] if idx < len(scenes) else None
        finding = {
            "scene_number": idx + 1,
            "invalid": False,
            "suspicious_text": False,
            "missing_characters": False,
            "invalid_listed_characters": [],
            "forbidden_words": [],
        }
        if not isinstance(scene, dict):
            finding["invalid"] = True
            finding["missing_characters"] = True
            missing_character_scenes += 1
            invalid_scenes += 1
            result["scene_findings"].append(finding)
            continue

        chars = scene.get("characters")
        if not isinstance(chars, list) or not chars:
            finding["missing_characters"] = True
            missing_character_scenes += 1
        else:
            invalid_chars = [
                c for c in chars
                if not isinstance(c, str) or c not in allowed
            ]
            if invalid_chars:
                finding["invalid_listed_characters"] = invalid_chars
                invalid_listed_character_scenes += 1

        text_fields = " ".join(
            str(scene.get(k, ""))
            for k in ("caption", "visual_description", "title")
        )
        found_words = sorted(set(m.group(0).lower() for m in forbidden_re.finditer(text_fields)))
        if found_words:
            finding["forbidden_words"] = found_words
            forbidden_word_scenes += 1
            finding["suspicious_text"] = True

        finding["invalid"] = bool(
            finding["missing_characters"]
            or finding["invalid_listed_characters"]
        )
        if finding["invalid"]:
            invalid_scenes += 1
        result["scene_findings"].append(finding)

    result["invalid_scenes"] = invalid_scenes
    result["missing_character_scenes"] = missing_character_scenes
    result["invalid_listed_character_scenes"] = invalid_listed_character_scenes
    result["forbidden_word_scenes"] = forbidden_word_scenes
    result["suspicious_text_scenes"] = forbidden_word_scenes
    result["drift_rate"] = invalid_scenes / SCENE_COUNT
    result["suspicious_text_rate"] = forbidden_word_scenes / SCENE_COUNT
    return result


def run_one(
    *,
    provider: str,
    api_key: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
    thinking: str,
    reasoning_effort: str,
    arm: str,
    scenario: str,
) -> dict[str, Any]:
    token = secrets.token_urlsafe(16) if arm == "token_gate" else None
    messages = [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": user_prompt(arm, token, scenario)},
    ]
    responses: list[dict[str, Any]] = []
    tool_reads: list[str] = []

    first = chat_completion(
        provider=provider,
        api_key=api_key,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        thinking=thinking,
        reasoning_effort=reasoning_effort,
    )
    responses.append(first)
    first_text = extract_text(first)

    final_text = first_text
    tool = maybe_parse_tool_request(final_text)
    max_reads = 24 if is_unlimited_read_scenario(scenario) else 1
    while arm == "control" and tool and len(tool_reads) < max_reads:
        tool_reads.append(tool["path"])
        messages.append({"role": "assistant", "content": final_text})
        continue_instruction = (
            "\nYou may request another file with the same read_file JSON, "
            "or write the final JSON scene plan now."
            if is_unlimited_read_scenario(scenario)
            else "\nNow write the final JSON scene plan. JSON only."
        )
        messages.append({
            "role": "user",
            "content": (
                f"Contents of {tool['path']}:\n"
                + read_rule_file(tool["path"])
                + continue_instruction
            ),
        })
        followup = chat_completion(
            provider=provider,
            api_key=api_key,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
        )
        responses.append(followup)
        final_text = extract_text(followup)
        tool = maybe_parse_tool_request(final_text)

    parsed = extract_json(final_text)
    score = score_output(parsed, arm, token)
    return {
        "arm": arm,
        "scenario": scenario,
        "provider": provider,
        "model": model,
        "thinking": thinking if provider == "deepseek" else None,
        "reasoning_effort": reasoning_effort if provider == "openrouter" else None,
        "temperature": temperature,
        "token": token,
        "tool_reads": tool_reads,
        "messages": messages,
        "responses": responses,
        "final_text": final_text,
        "parsed": parsed,
        "score": score,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "scene_count": SCENE_COUNT,
        "arms": {},
    }
    for arm in ARMS:
        arm_results = [r for r in results if r["arm"] == arm]
        rates = [r["score"]["drift_rate"] for r in arm_results]
        suspicious_rates = [r["score"].get("suspicious_text_rate", 0.0) for r in arm_results]
        invalid_json = sum(not r["score"]["ok_json"] for r in arm_results)
        scene_count_errors = sum(r["score"]["scene_count_error"] for r in arm_results)
        token_errors = sum(r["score"]["token_error"] for r in arm_results)
        tool_reads = sum(1 for r in arm_results if r["tool_reads"])
        summary["arms"][arm] = {
            "runs": len(arm_results),
            "mean_drift_rate": statistics.mean(rates) if rates else None,
            "variance": statistics.pvariance(rates) if len(rates) > 1 else 0.0,
            "stddev": statistics.pstdev(rates) if len(rates) > 1 else 0.0,
            "mean_suspicious_text_rate": statistics.mean(suspicious_rates) if suspicious_rates else None,
            "min_drift_rate": min(rates) if rates else None,
            "max_drift_rate": max(rates) if rates else None,
            "invalid_json_runs": invalid_json,
            "scene_count_error_runs": scene_count_errors,
            "token_error_runs": token_errors,
            "control_tool_read_runs": tool_reads,
        }
    return summary


def write_markdown(summary: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Context Gate Experiment Results",
        "",
        "| Arm | Runs | Mean drift | Stddev | Variance | Invalid JSON | Scene count errors | Receipt errors | Tool reads |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm in ARMS:
        s = summary["arms"][arm]
        lines.append(
            f"| {arm} | {s['runs']} | {s['mean_drift_rate']:.3f} | "
            f"{s['stddev']:.3f} | {s['variance']:.3f} | "
            f"{s['invalid_json_runs']} | {s['scene_count_error_runs']} | "
            f"{s['token_error_runs']} | {s['control_tool_read_runs']} |"
        )
    lines.append("")
    lines.append("Drift means: a scene listed a character outside the rulebook, or omitted characters entirely.")
    lines.append("Suspicious fantasy words in descriptions are tracked in summary.json but not counted as character drift.")
    out_path.write_text("\n".join(lines) + "\n")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Run the Context Gate hallucination experiment.")
    p.add_argument("--runs", type=int, default=3, help="runs per arm")
    p.add_argument("--provider", choices=sorted(DEFAULT_MODEL_BY_PROVIDER), default="openrouter")
    p.add_argument("--model", default=None)
    p.add_argument("--scenario", choices=SCENARIOS, default="baseline")
    p.add_argument("--thinking", choices=("disabled", "enabled"), default="disabled", help="DeepSeek only")
    p.add_argument(
        "--reasoning-effort",
        choices=("none", "minimal", "low", "medium", "high", "xhigh"),
        default="none",
        help="OpenRouter reasoning effort",
    )
    p.add_argument("--temperature", type=float, default=0.9)
    p.add_argument("--max-tokens", type=int, default=5000)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--env-file", default=".env", help="optional .env file containing API keys")
    p.add_argument("--sleep", type=float, default=0.2, help="seconds between calls")
    args = p.parse_args(argv)

    if args.env_file:
        env_path = Path(args.env_file).expanduser()
        if env_path.exists():
            load_dotenv(env_path)

    api_key_name = "OPENROUTER_API_KEY" if args.provider == "openrouter" else "DEEPSEEK_API_KEY"
    api_key = os.environ.get(api_key_name)
    if not api_key:
        print(f"ERROR: {api_key_name} is not set. Use env var or --env-file.", file=sys.stderr)
        return 2
    model = args.model or DEFAULT_MODEL_BY_PROVIDER[args.provider]

    out_dir = Path(args.out_dir or f"results/{now_slug()}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "raw").mkdir(exist_ok=True)
    (out_dir / "authority.json").write_text(authority_text() + "\n")
    rules_dir = out_dir / "rules"
    rules_dir.mkdir(exist_ok=True)
    for path in sorted(p for p in RULE_FILE_TEXTS if p.startswith("rules/")):
        (out_dir / path).write_text(read_rule_file(path).rstrip() + "\n")

    all_results: list[dict[str, Any]] = []
    config = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "provider": args.provider,
        "model": model,
        "scenario": args.scenario,
        "thinking": args.thinking if args.provider == "deepseek" else None,
        "reasoning_effort": args.reasoning_effort if args.provider == "openrouter" else None,
        "temperature": args.temperature,
        "runs_per_arm": args.runs,
        "arms": ARMS,
        "scene_count": SCENE_COUNT,
    }
    (out_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")

    for i in range(1, args.runs + 1):
        for arm in ARMS:
            print(f"[run] {arm} {i}/{args.runs}", flush=True)
            try:
                result = run_one(
                    api_key=api_key,
                    provider=args.provider,
                    model=model,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                    thinking=args.thinking,
                    reasoning_effort=args.reasoning_effort,
                    arm=arm,
                    scenario=args.scenario,
                )
            except Exception as e:
                result = {
                    "arm": arm,
                    "scenario": args.scenario,
                    "provider": args.provider,
                    "model": model,
                    "temperature": args.temperature,
                    "reasoning_effort": args.reasoning_effort if args.provider == "openrouter" else None,
                    "error": str(e),
                    "tool_reads": [],
                    "score": {
                        "ok_json": False,
                        "scene_count": 0,
                        "required_scene_count": SCENE_COUNT,
                        "invalid_scenes": SCENE_COUNT,
                        "suspicious_text_scenes": 0,
                        "missing_character_scenes": SCENE_COUNT,
                        "invalid_listed_character_scenes": 0,
                        "forbidden_word_scenes": 0,
                        "scene_count_error": True,
                        "token_error": arm == "token_gate",
                        "drift_rate": 1.0,
                        "suspicious_text_rate": 0.0,
                        "errors": [str(e)],
                        "scene_findings": [],
                    },
                }
            result["run_index"] = i
            all_results.append(result)
            raw_path = out_dir / "raw" / f"{arm}-{i:03d}.json"
            raw_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
            score = result["score"]
            print(
                f"      drift={score['drift_rate']:.3f} "
                f"invalid_scenes={score['invalid_scenes']}/{SCENE_COUNT} "
                f"tool_reads={len(result.get('tool_reads', []))}",
                flush=True,
            )
            if args.sleep:
                time.sleep(args.sleep)

    summary = summarize(all_results)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_markdown(summary, out_dir / "summary.md")
    print()
    print((out_dir / "summary.md").read_text())
    print(f"[done] wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
