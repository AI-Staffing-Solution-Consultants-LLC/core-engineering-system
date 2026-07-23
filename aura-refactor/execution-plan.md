# Aura Refactor — AWS Deployment Execution Plan

## Overview

Deploy the `refactor.py` and `identity-check.py` tools to AWS for running against
code repositories in S3 or EC2-based environments.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  AWS Step Functions / CodeBuild                      │
│  ┌──────────────────────────────────────────────┐    │
│  │  1. Clone repo from CodeCommit / S3          │    │
│  │  2. Run refactor.py in container             │    │
│  │  3. Run identity-check.py                    │    │
│  │  4. Push changes back / create PR            │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

## Step-by-Step Instructions

### 1. Package the Tools

```bash
# From project root
cd aura-refactor/
zip aura-refactor-tools.zip refactor.py identity-check.py
```

Upload to S3:
```bash
aws s3 cp aura-refactor-tools.zip s3://<your-bucket>/artifacts/aura-refactor-tools.zip
```

### 2. Create an AWS CodeBuild Project

```bash
aws codebuild create-project \
  --name aura-refactor \
  --source '{
    "type": "S3",
    "location": "<your-bucket>/artifacts/aura-refactor-tools.zip"
  }' \
  --artifacts '{"type": "NO_ARTIFACTS"}' \
  --environment '{
    "type": "LINUX_CONTAINER",
    "image": "aws/codebuild/standard:7.0",
    "computeType": "BUILD_GENERAL1_SMALL"
  }' \
  --service-role "arn:aws:iam::<account>:role/codebuild-service-role" \
  --buildspec '{
    "version": "0.2",
    "phases": {
      "install": {"commands": ["echo No dependencies needed"]},
      "build": {
        "commands": [
          "echo Running Aura refactor...",
          "python3 refactor.py --target-path ./repo --dry-run",
          "echo Dry-run complete. Remove --dry-run to execute."
        ]
      },
      "post_build": {
        "commands": [
          "echo Running identity check...",
          "python3 identity-check.py --target-path ./repo"
        ]
      }
    }
  }'
```

### 3. Alternative: AWS Lambda (Lightweight)

For smaller repositories (< 512 MB):

```bash
# Create Lambda layer with the scripts
zip layer.zip refactor.py identity-check.py
aws lambda publish-layer-version \
  --layer-name aura-refactor-tools \
  --zip-file fileb://layer.zip \
  --compatible-runtimes python3.11 python3.12

# Create Lambda function
aws lambda create-function \
  --function-name aura-refactor \
  --runtime python3.12 \
  --role arn:aws:iam::<account>:role/lambda-refactor-role \
  --handler refactor.main \
  --layers arn:aws:lambda:<region>:<account>:layer:aura-refactor-tools:1 \
  --timeout 900 \
  --memory-size 1024
```

### 4. Alternative: EC2 Run Command

For existing EC2 instances with the repo cloned:

```bash
# Upload scripts
aws s3 cp refactor.py s3://<bucket>/scripts/refactor.py
aws s3 cp identity-check.py s3://<bucket>/scripts/identity-check.py

# Execute via SSM Run Command
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --targets "Key=instanceIds,Values=i-1234567890abcdef0" \
  --parameters '{
    "commands": [
      "aws s3 cp s3://<bucket>/scripts/refactor.py /tmp/refactor.py",
      "aws s3 cp s3://<bucket>/scripts/identity-check.py /tmp/identity-check.py",
      "python3 /tmp/refactor.py --target-path /home/ec2-user/repo --dry-run",
      "python3 /tmp/identity-check.py --target-path /home/ec2-user/repo"
    ]
  }'
```

### 5. Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::<your-bucket>/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### 6. Execution Order (Critical)

1. **Run in dry-run mode first** — audit the proposed changes:
   ```bash
   python3 refactor.py --target-path /path/to/repo --dry-run
   ```

2. **Review the dry-run output** — confirm all renames are expected.

3. **Checkout a new git branch** (if the repo is under version control).

4. **Execute the refactor**:
   ```bash
   python3 refactor.py --target-path /path/to/repo
   ```

5. **Verify with identity check**:
   ```bash
   python3 identity-check.py --target-path /path/to/repo
   ```
   Must exit 0 with "PASS".

6. **Review the diff and commit** the changes.

### 7. Exclusion Patterns

Default exclusions (hard-coded): `vendor`, `node_modules`, `.git`

Add custom exclusions at runtime:
```bash
python3 refactor.py --target-path /path/to/repo --exclude build --exclude dist --exclude terraform
```

### 8. Rollback

The tools are **destructive** when run without `--dry-run`. Rollback requires:
- Git: `git checkout . && git clean -fd`
- No VCS: Restore from the S3 backup created before execution.

Always run with `--dry-run` first and commit changes incrementally.
