import os
import json
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import BadRequest
from ssh_utils import run_ssh_command
from commands import COMMANDS

CONFIG_FILE = "config.json"
SERVERS_FILE = Path("servers.json")

if not Path(CONFIG_FILE).exists():
    print("❌ لطفاً فایل config.json را پر کنید.")
    exit(1)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

ALLOWED_USERS = CONFIG.get("allowed_users", [])
BOT_TOKEN = CONFIG.get("bot_token") or os.environ.get("TG_BOT_TOKEN")

# init servers file if missing
if not SERVERS_FILE.exists():
    SERVERS_FILE.write_text(json.dumps({"servers": [], "selected": None}, indent=2))

def load_data():
    with open(SERVERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(SERVERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

PENDING = {}  # user_id -> {"type": "port"/"password", "server": name, "cmd": cmd_key}

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("🚫 شما مجاز به استفاده از این ربات نیستید.")
        return
    kb = [
        [InlineKeyboardButton("➕ افزودن سرور", callback_data="add_server")],
        [InlineKeyboardButton("📋 لیست سرورها", callback_data="list_servers")]
    ]
    await update.message.reply_text("📋 منوی اصلی:", reply_markup=InlineKeyboardMarkup(kb))

async def add_server_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /addserver name host port user password
    if update.effective_user.id not in ALLOWED_USERS:
        return
    args = context.args
    if len(args) < 5:
        await update.message.reply_text("❌ فرمت: /addserver <name> <host> <port> <user> <password>")
        return
    name, host, port, user, password = args[0], args[1], args[2], args[3], args[4]
    data = load_data()
    servers = data.get("servers", [])
    if any(s["name"] == name for s in servers):
        await update.message.reply_text("❌ نام سرور تکراری است. از نام دیگر استفاده کنید.")
        return
    servers.append({"name": name, "host": host, "port": str(port), "user": user, "password": password, "key_path": None})
    data["servers"] = servers
    save_data(data)
    await update.message.reply_text(f"✅ سرور *{name}* اضافه شد.", parse_mode="Markdown")

async def list_servers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    servers = data.get("servers", [])

    q = update.callback_query

    if not servers:
        if q:
            await q.message.reply_text("📭 هیچ سروری اضافه نشده.")
        else:
            await update.message.reply_text("📭 هیچ سروری اضافه نشده.")
        return

    kb = [
        [InlineKeyboardButton(s["name"], callback_data=f"select:{s['name']}")]
        for s in servers
    ]

    if q:
        await q.message.reply_text("📋 سرورها:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("📋 سرورها:", reply_markup=InlineKeyboardMarkup(kb))
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        # قدیمی یا زمان گذشته — بی‌خیال
        return

    user_id = q.from_user.id
    if not is_allowed(user_id):
        await q.edit_message_text("🚫 شما مجاز به اجرای این دستور نیستید.")
        return

    data = q.data

    if data == "add_server":
        await q.edit_message_text("📌 برای افزودن سرور از این دستور استفاده کن:\n`/addserver <name> <host> <port> <user> <password>`", parse_mode="Markdown")
        return

    if data == "list_servers":
        await list_servers_cmd(update, context)
        return

    if data.startswith("select:"):
        name = data.split(":", 1)[1]
        d = load_data()
        # set selected
        d["selected"] = name
        save_data(d)
        # build server menu (commands)
        kb = []
        for k, v in COMMANDS.items():
            kb.append([InlineKeyboardButton(v["desc"], callback_data=f"cmd:{name}:{k}")])
        kb.append([InlineKeyboardButton("🗑 حذف سرور", callback_data=f"delete:{name}")])
        kb.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="list_servers")])
        await q.edit_message_text(f"📡 سرور *{name}* انتخاب شد.\nدستور مورد نظر را انتخاب کنید:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("delete:"):
        name = data.split(":",1)[1]
        d = load_data()
        d["servers"] = [s for s in d.get("servers", []) if s["name"] != name]
        if d.get("selected") == name:
            d["selected"] = None
        save_data(d)
        await q.edit_message_text(f"🗑 سرور *{name}* حذف شد.", parse_mode="Markdown")
        return

    if data.startswith("cmd:"):
        # cmd:<server>:<cmdkey>
        _, name, cmdkey = data.split(":",2)
        d = load_data()
        server = next((s for s in d.get("servers", []) if s["name"] == name), None)
        if not server:
            await q.edit_message_text("❌ سرور پیدا نشد.")
            return
        cmd_def = COMMANDS.get(cmdkey)
        if not cmd_def:
            await q.edit_message_text("❌ دستور نامعتبر.")
            return

        if cmd_def.get("interactive"):
            # store pending
            PENDING[update.effective_user.id] = {"type": cmd_def["interactive"], "server": name, "cmd": cmdkey}
            if cmd_def["interactive"] == "port":
                await q.edit_message_text("🔢 لطفاً پورت جدید را بفرستید:")
            elif cmd_def["interactive"] == "password":
                await q.edit_message_text("🔑 لطفاً پسورد جدید را بفرستید:")
            return

        if cmd_def.get("confirm"):
            kb = [
                [InlineKeyboardButton("✔️ بله، اجرا کن", callback_data=f"exec:{name}:{cmdkey}")],
                [InlineKeyboardButton("❌ لغو", callback_data=f"cancel")]
            ]
            await q.edit_message_text(f"⚠️ آیا مطمئن هستی می‌خواهی `{cmd_def['desc']}` را برای *{name}* اجرا کنی؟", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            return

        await q.edit_message_text("⏳ در حال اجرا ...")
        out = run_ssh_command(server["host"], server["port"], server["user"], server.get("password"), cmd_def["script"], key_path=server.get("key_path"))
        # fancy status formatting
        if cmdkey == "status":
            # attempt to parse the status output (we used tags in commands.py)
            lines = out.splitlines()
            result = "📊 نتیجه وضعیت:\n\n"
            for L in lines:
                result += L + "\n"
            await q.edit_message_text(f"```\n{result}\n```", parse_mode="Markdown")
        else:
            if not out.strip():
                out = "✅ انجام شد."
            await q.edit_message_text(f"```\n{out}\n```", parse_mode="Markdown")
        return

    if data == "cancel":
        await q.edit_message_text("❌ عملیات لغو شد.")
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # handle interactive pending inputs (port/password)
    uid = update.effective_user.id
    if uid not in PENDING:
        return
    info = PENDING.pop(uid)
    typ = info["type"]
    server_name = info["server"]
    cmdkey = info["cmd"]
    d = load_data()
    server = next((s for s in d.get("servers", []) if s["name"] == server_name), None)
    if not server:
        await update.message.reply_text("❌ سرور پیدا نشد (موقتی).")
        return
    cmd_def = COMMANDS.get(cmdkey)
    script = cmd_def["script"]
    if typ == "port":
        script = script.format(port=update.message.text)
    elif typ == "password":
        script = script.format(user=server["user"], newpass=update.message.text)
    await update.message.reply_text("⏳ در حال اجرا ...")
    out = run_ssh_command(server["host"], server["port"], server["user"], server.get("password"), script, key_path=server.get("key_path"))
    if not out.strip():
        out = "✅ انجام شد."
    await update.message.reply_text(f"```\n{out}\n```", parse_mode="Markdown")

def main():
    if not BOT_TOKEN:
        print("❌ bot_token در config.json تنظیم نشده.")
        return
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("addserver", add_server_cmd))
    app.add_handler(CommandHandler("listservers", list_servers_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🤖 ربات اجرا شد.")
    app.run_polling()

if __name__ == "__main__":
    main()