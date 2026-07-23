## BLOCKER-001: Subagent API billing depleted (2026-07-21)
- **Severity**: CRITICAL — blocks all 29 implementation tasks
- **Symptom**: Every `task()` call returns "Insufficient USD balance for automatic replenishment"
- **Model**: deepseek-v4-pro (opencode-go/deepseek-v4-pro)
- **Impact**: Zero implementation progress possible
- **Resolution**: Add funds to trading account to restore subagent execution
- **Workaround**: None — orchestrator cannot write code directly per system rules
