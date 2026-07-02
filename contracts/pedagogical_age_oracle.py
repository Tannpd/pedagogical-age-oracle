# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
import typing
from dataclasses import dataclass


@allow_storage
@dataclass
class SuitabilityRecord:
    material_snippet: str
    target_age_group: str
    suitability: str  # APPROPRIATE | NEEDS_ADJUSTMENT | INAPPROPRIATE
    confidence: bigint
    feedback: str


def _normalize_suitability(suitability: str) -> str:
    s = str(suitability or "").strip().upper()
    if "APPROPRIATE" in s:
        return "APPROPRIATE"
    if "ADJUSTMENT" in s or "NEEDS" in s or "ADJUST" in s:
        return "NEEDS_ADJUSTMENT"
    if "INAPPROPRIATE" in s or "UNSUITABLE" in s:
        return "INAPPROPRIATE"
    return "INAPPROPRIATE"


def _normalize_confidence(conf_val: typing.Any) -> int:
    try:
        c = int(conf_val)
    except Exception:
        c = 0
    return max(0, min(100, c))


class Contract(gl.Contract):
    evaluations: TreeMap[str, SuitabilityRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

    @gl.public.write
    def evaluate_material(self, material_snippet: str, target_age_group: str) -> None:
        if not material_snippet or not material_snippet.strip():
            raise gl.vm.UserError("material_snippet must not be empty")
        if not target_age_group or not target_age_group.strip():
            raise gl.vm.UserError("target_age_group must not be empty")

        snippet_clean = material_snippet.strip()
        age_clean = target_age_group.strip()

        def leader_fn() -> str:
            prompt = f"""You are a primary school education and child development expert.
Evaluate the provided material snippet to determine if its vocabulary, sentence structure, conceptual complexity, and tone are age-appropriate for the target age group.

MATERIAL SNIPPET:
---
{snippet_clean}
---

TARGET AGE GROUP:
---
{age_clean}
---

Rules for pedagogical evaluation:
- Assign "APPROPRIATE" if the language, complexity, and content are a perfect fit for the target age group's cognitive and reading level.
- Assign "NEEDS_ADJUSTMENT" if the content is conceptually correct but uses vocabulary that is slightly too advanced, has sentences that are too long, or has minor tone issues that can be fixed.
- Assign "INAPPROPRIATE" if the content is far too advanced (e.g. university physics for preschool), completely unsuitable in tone, or contains concepts inappropriate for the child's development.
- Assign a confidence score from 0 to 100 representing how confident you are in this pedagogical grade.
- Provide a brief, supportive feedback message (maximum 200 characters) explaining your assessment.

Respond ONLY with a valid JSON object matching the following structure:
{{
  "suitability": "APPROPRIATE" | "NEEDS_ADJUSTMENT" | "INAPPROPRIATE",
  "confidence": <integer 0-100>,
  "feedback": "feedback string"
}}"""
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict):
                res = {}
            
            suitability = _normalize_suitability(res.get("suitability", "INAPPROPRIATE"))
            confidence = _normalize_confidence(res.get("confidence", 0))
            feedback = str(res.get("feedback", "")).strip()[:200]
            if not feedback:
                feedback = "No feedback provided."

            return json.dumps({
                "suitability": suitability,
                "confidence": confidence,
                "feedback": feedback
            }, sort_keys=True)

        def validator_fn(leader_res: typing.Any) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_res.calldata)
            except Exception:
                return False

            leader_suitability = _normalize_suitability(leader_data.get("suitability"))
            leader_confidence = _normalize_confidence(leader_data.get("confidence"))

            try:
                mine_json = leader_fn()
                mine_data = json.loads(mine_json)
            except Exception:
                return False

            mine_suitability = _normalize_suitability(mine_data.get("suitability"))
            mine_confidence = _normalize_confidence(mine_data.get("confidence"))

            if leader_suitability != mine_suitability:
                return False

            if abs(leader_confidence - mine_confidence) > 15:
                return False

            return True

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        payload = json.loads(raw_result)

        rid = str(self.next_id)
        self.evaluations[rid] = SuitabilityRecord(
            material_snippet=snippet_clean,
            target_age_group=age_clean,
            suitability=_normalize_suitability(payload.get("suitability")),
            confidence=bigint(_normalize_confidence(payload.get("confidence"))),
            feedback=str(payload.get("feedback")).strip()[:200]
        )
        self.next_id = self.next_id + bigint(1)

    @gl.public.view
    def get_evaluation(self, eval_id: str) -> str:
        if eval_id not in self.evaluations:
            raise gl.vm.UserError("Evaluation record not found")
        
        record = self.evaluations[eval_id]
        return json.dumps({
            "id": eval_id,
            "material_snippet": record.material_snippet,
            "target_age_group": record.target_age_group,
            "suitability": record.suitability,
            "confidence": int(record.confidence),
            "feedback": record.feedback
        })

    @gl.public.view
    def get_total_evaluations(self) -> int:
        return int(self.next_id)
