# 🚀 Telegram Server Manager

ربات مدیریت چند سرور از یک مستر:

- ➕ افزودن سرور
- 📋 لیست سرورها
- 📊 وضعیت سیستم
- 🔄 ریبوت / ⏹ خاموش کردن
- 🔑 تغییر پسورد
- 🔥 مدیریت فایروال

## ⚙️ نصب سریع

```bash
curl -fsSL https://raw.githubusercontent.com/aminborna/telegram-server-manager/main/install.sh | bash
```

## 🔑 تنظیمات

فایل `config.json` را ویرایش کنید و `bot_token` و `allowed_users` را وارد کنید.

## ▶️ اجرا

سرویس به صورت خودکار فعال می‌شود:

```bash
sudo systemctl status telegram-server-manager
sudo journalctl -u telegram-server-manager -f
```
