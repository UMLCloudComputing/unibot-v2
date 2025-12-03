#!/usr/bin/env bash
set -euo pipefail

echo "Finding CloudFormation stacks starting with 'eksctl' ..."

STACKS=$(aws cloudformation list-stacks \
    --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE \
    --query "StackSummaries[?starts_with(StackName, 'eksctl')].StackName" \
    --output text)

if [[ -z "$STACKS" ]]; then
    echo "No stacks found that start with 'eksctl'."
    exit 0
fi

echo "Disabling termination protection on the following stacks:"
echo "$STACKS"
echo

for STACK in $STACKS; do
    echo "Processing stack: $STACK"
    aws cloudformation update-termination-protection \
        --stack-name "$STACK" \
        --no-enable-termination-protection
    echo "Termination protection disabled on: $STACK"
done

echo "All eksctl* stacks updated."

