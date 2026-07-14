package core.constitutional

# Every tool call must be traceable to a reasoning step.
# This builds the tamper-evident ledger for post-mortem replay.

deny[msg] {
    input.action == "tool_call"
    not input.reasoning_log_ref
    msg := "Constitutional AI: every tool call must reference a reasoning log entry"
}
