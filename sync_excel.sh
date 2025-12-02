#!/bin/bash
# sync_excel.sh
# Simple helper to upload the local Excel file to the remote VM via scp.

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <user@host> <remote_path>"
  echo "Example: $0 ubuntu@1.2.3.4 /home/ubuntu/streamlit_reportes/BBDD_MANTENCION.xlsm"
  exit 1
fi

REMOTE=$1
REMOTE_PATH=$2
LOCAL_FILE="BBDD_MANTENCION.xlsm"

if [ ! -f "$LOCAL_FILE" ]; then
  echo "Local file $LOCAL_FILE not found. Ensure you run this from the project folder containing the Excel file."
  exit 2
fi

echo "Uploading $LOCAL_FILE to $REMOTE:$REMOTE_PATH..."
scp "$LOCAL_FILE" "$REMOTE:$REMOTE_PATH"
echo "Upload complete. If app caches data, restart the service on the VM:"
echo "  ssh $REMOTE 'sudo systemctl restart streamlit-reportes.service'"
