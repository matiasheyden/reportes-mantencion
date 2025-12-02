#!/bin/bash
# deploy_to_vm.sh
# Script to prepare an Ubuntu VM for the Streamlit app. Run on the VM as a sudo user.

set -euo pipefail

WORKDIR="/home/ubuntu/streamlit_reportes"
REPO_URL="" # <--- replace with your git repo url if you push this project to git

echo "Updating packages..."
sudo apt update && sudo apt upgrade -y

echo "Installing required packages..."
sudo apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx git

echo "Creating app directory: $WORKDIR"
sudo mkdir -p "$WORKDIR"
sudo chown $USER:$USER "$WORKDIR"
cd "$WORKDIR"

if [ -n "$REPO_URL" ]; then
  echo "Cloning repository..."
  git clone "$REPO_URL" .
else
  echo "No REPO_URL set. Copy project files to $WORKDIR manually or set REPO_URL in this script."
fi

echo "Creating virtualenv..."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  pip install streamlit pandas openpyxl plotly reportlab dataframe_image
fi

echo "Creating systemd service file..."
sudo tee /etc/systemd/system/streamlit-reportes.service > /dev/null <<'EOF'
[Unit]
Description=Streamlit Reportes de Mantencion
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$WORKDIR
Environment="PATH=$WORKDIR/.venv/bin"
ExecStart=$WORKDIR/.venv/bin/python -m streamlit run $WORKDIR/app.py --server.headless true --server.port 8501 --server.address 127.0.0.1
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable streamlit-reportes.service
sudo systemctl start streamlit-reportes.service
sudo systemctl status streamlit-reportes.service --no-pager

echo "Configuring nginx reverse proxy (create site conf and enable it)..."
sudo tee /etc/nginx/sites-available/streamlit_reportes > /dev/null <<'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://127.0.0.1:8501/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/streamlit_reportes /etc/nginx/sites-enabled/streamlit_reportes
sudo nginx -t
sudo systemctl restart nginx

echo "If you have a domain, run certbot to get a certificate (replace YOUR_DOMAIN):"
echo "  sudo certbot --nginx -d YOUR_DOMAIN"

echo "Deploy script finished. Remember to upload your Excel file to $WORKDIR/BBDD_MANTENCION.xlsm (via scp/sftp) and adjust file permissions."
