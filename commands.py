COMMANDS = {
    "status": {
        "desc": "📊 وضعیت سیستم",
        "script": "echo \"UPTIME: $(uptime -p)\"; echo \"LOAD: $(cat /proc/loadavg | awk '{print $1\", \"$2\", \"$3}')\"; echo \"DISK: $(df -h --total | awk '/total/ {print $2\" \" $3\" \" $4\" \"$5\" \"$6}')\"; free -m | awk 'NR==2{printf \"Used: %sMB / %sMB (%.1f%%)\", $3,$2,$3*100/$2 }'"
    },
    "reboot": {
        "desc": "🔄 ریبوت سرور",
        "script": "sudo reboot",
        "confirm": True
    },
    "shutdown": {
        "desc": "⏹ خاموش کردن سرور",
        "script": "sudo shutdown -h now",
        "confirm": True
    },
    "install_firewall": {
        "desc": "🛡 نصب فایروال (ufw/firewalld)",
        "script": "if command -v apt >/dev/null 2>&1; then sudo apt update && sudo apt install -y ufw; elif command -v yum >/dev/null 2>&1; then sudo yum install -y firewalld; fi",
        "confirm": True
    },
    "allow_port": {
        "desc": "➕ باز کردن پورت",
        "script": "if command -v ufw >/dev/null 2>&1; then sudo ufw allow {port}/tcp; elif command -v firewall-cmd >/dev/null 2>&1; then sudo firewall-cmd --permanent --add-port={port}/tcp && sudo firewall-cmd --reload; fi",
        "interactive": "port",
        "confirm": True
    },
    "deny_port": {
        "desc": "🚫 بستن پورت",
        "script": "if command -v ufw >/dev/null 2>&1; then sudo ufw deny {port}/tcp; elif command -v firewall-cmd >/dev/null 2>&1; then sudo firewall-cmd --permanent --remove-port={port}/tcp && sudo firewall-cmd --reload; fi",
        "interactive": "port",
        "confirm": True
    },
    "change_port": {
        "desc": "🔀 تغییر پورت SSH",
        "script": "sudo sed -i 's/^#*Port .*/Port {port}/' /etc/ssh/sshd_config && sudo systemctl restart sshd",
        "interactive": "port",
        "confirm": True
    },
    "change_password": {
        "desc": "🔒 تغییر پسورد (کاربر)",
        "script": "echo '{user}:{newpass}' | sudo chpasswd",
        "interactive": "password",
        "confirm": True
    }
}