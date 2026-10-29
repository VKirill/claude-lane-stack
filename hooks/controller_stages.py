"""Run stages shared by the controller and the PM stop sentinel.

A stage in ACTIVE_STAGES still has work. TERMINAL_STAGES is finished.
"""

TERMINAL_STAGES = frozenset({"accepted", "blocked", "failed"})
ACTIVE_STAGES = frozenset({"running", "degraded"})
