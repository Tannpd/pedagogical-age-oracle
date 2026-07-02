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


class Contract(gl.Contract):
    evaluations: TreeMap[str, SuitabilityRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

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
