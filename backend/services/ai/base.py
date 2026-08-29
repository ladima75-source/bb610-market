from __future__ import annotations
from dataclasses import dataclass

@dataclass
class AIResult:
    output:dict
    provider:str
    model:str|None=None

class AIProvider:
    provider='unconfigured'
    def configured(self)->bool:return False
    def run(self,job_type:str,context:dict)->AIResult:raise RuntimeError('AI provider is not configured')
