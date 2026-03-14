#!/bin/bash
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name')

if [ "$TOOL" = "Read" ]; then
  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path')
elif [ "$TOOL" = "Grep" ]; then
  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.path // ""')
else
  exit 0
fi

# Block if the path ends with /.env or is exactly .env
if echo "$FILE_PATH" | grep -qE '(^|/)\.env$'; then
  echo "Blocked: Reading .env is not permitted." >&2
  exit 2
fi

exit 0