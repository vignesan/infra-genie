#!/bin/sh
# entrypoint.sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Check if required environment variables are set
if [ -z "$ADO_ORG_URL" ] || [ -z "$ADO_PROJECT" ] || [ -z "$ADO_PAT" ]; then
  echo "Error: ADO_ORG_URL, ADO_PROJECT, and ADO_PAT environment variables must be set." >&2
  exit 1
fi

# Create the JSON configuration file
cat <<EOF > /usr/src/app/.azure-devops.json
{
  "organizationUrl": "$ADO_ORG_URL",
  "project": "$ADO_PROJECT",
  "pat": "$ADO_PAT"
}
EOF

# Execute the main container command (passed as arguments to this script)
exec "$@"
