package core.constitutional

# Reject any action that claims broad Write scope without a specific target.
# Write("*") is never acceptable.

deny[msg] {
    input.scope == "write"
    input.target == "*"
    msg := "Constitutional AI: broad Write scope is denied; require namespace scope"
}
