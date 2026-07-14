package core.constitutional

# Remediation agents must declare a namespace before acting.
# Unscoped remediation is too dangerous.

deny[msg] {
    input.agent_role == "remediation"
    not input.namespace
    msg := "Constitutional AI: remediation agents must declare a namespace"
}
