package core.constitutional

# Prevent terraform destroy on production environments.
# This is a hard kill — the LLM's intent is irrelevant.

deny[msg] {
    input.command == "terraform"
    input.args[_] == "destroy"
    input.env == "prod"
    msg := "Constitutional AI: terraform destroy on prod is denied"
}
