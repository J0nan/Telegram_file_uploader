import os

API_ID =  os.environ.get("TG_API_ID")
API_HASH = os.environ.get("TG_API_HASH")
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
SESSION = os.environ.get("TG_SESSION", "uploader")

SEND_FILES_DIR = os.environ.get("BOT_UPLOAD_DIR", "/sendFiles")

AUTHORIZED_USERS_ID = os.environ.get("TG_AUTHORIZED_USERS_ID", False)

UPDATE_UPLOAD_INTERVAL = float(os.environ.get("BOT_UPDATE_UPLOAD_INTERVAL", 10))

SEND_PUBLIC_IP = str(os.environ.get("SEND_PUBLIC_IP", False))
