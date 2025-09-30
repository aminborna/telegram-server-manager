
#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt/telegram-server-manager"
SERVICE_NAME="telegram-server-manager"
RUN_AS_USER="root"

echo "🚀 شروع نصب Telegram Server Manager ..."

sudo mkdir -p "$INSTALL_DIR"
sudo chown $USER:$USER "$INSTALL_DIR"

echo "📦 نصب پیش‌نیازها..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3.10-venv git

rm -rf "$INSTALL_DIR/venv"

if [ ! -d "$INSTALL_DIR/.git" ]; then
  git clone https://github.com/aminborna/telegram-server-manager.git "$INSTALL_DIR"
else
  cd "$INSTALL_DIR"
  git pull
fi

cd "$INSTALL_DIR"


if [ ! -f servers.json ]; then
  echo '{"servers": [], "selected": null}' > servers.json
fi


echo "🐍 ساخت venv ..."
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "⚙️ ساخت سرویس systemd ..."
sudo bash -c "cat > /etc/systemd/system/${SERVICE_NAME}.service <<SERVICE
[Unit]
Description=Telegram Server Manager Bot
After=network.target

[Service]
Type=simple
User=$RUN_AS_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE"

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

echo "✅ نصب کامل شد!"
echo "👉 لاگ‌ها: sudo journalctl -u $SERVICE_NAME -f"