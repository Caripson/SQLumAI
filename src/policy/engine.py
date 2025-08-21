from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Event:
    database: Optional[str]
    user: Optional[str]
    sql_text: Optional[str]
    table: Optional[str]
    column: Optional[str]
    value: Optional[str]


@dataclass
class PolicyDecision:
    action: str  # allow|block|autocorrect
    reason: str
    confidence: float = 1.0
    corrected_value: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class Rule:
    id: str
    target: str  # table|column|pattern
    selector: str
    action: str
    reason: str = ""
    confidence: float = 1.0
    enabled: bool = True


class PolicyEngine:
    def __init__(self, rules: List[Rule], environment: Optional[str] = None):
        self.rules = rules
        self.environment = (environment or "").lower()
        self._rule_index = {r.id: r for r in rules}

    def decide(self, event: Event) -> PolicyDecision:
        for r in self.rules:
            if not getattr(r, "enabled", True):
                continue
            if getattr(r, "apply_in_envs", None):
                envs = [e.lower() for e in getattr(r, "apply_in_envs", [])]
                if self.environment and self.environment not in envs:
                    continue
            if r.target == "table" and event.table and r.selector.lower() == event.table.lower():
                return PolicyDecision(r.action, r.reason, r.confidence, None, r.id)
            if r.target == "column" and event.column:
                sel = r.selector.lower()
                col = event.column.lower()
                if "." in sel:
                    if sel == col:
                        return PolicyDecision(r.action, r.reason, r.confidence, None, r.id)
                else:
                    # column-only match (e.g., selector "Email" matches dbo.Users.Email or param name Email)
                    last_seg = col.split(".")[-1].lstrip("@")
                    if sel.lstrip("@") == last_seg:
                        return PolicyDecision(r.action, r.reason, r.confidence, None, r.id)
            if r.target == "pattern" and event.sql_text and r.selector.lower() in event.sql_text.lower():
                return PolicyDecision(r.action, r.reason, r.confidence, None, r.id)
        return PolicyDecision("allow", "no matching rule", 1.0, None, None)

    def get_rule(self, rule_id: Optional[str]) -> Optional[Rule]:
        if not rule_id:
            return None
        return self._rule_index.get(rule_id)
