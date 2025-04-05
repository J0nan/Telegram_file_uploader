from telethon import TelegramClient, events, Button
import os
import subprocess
import re
import requests
from configs.bot_config import *
from utils.lang_map import lang_map_code
import asyncio
import json
import flagz

seven_zip_pattern = re.compile(r"\.7z\..*$")

client = TelegramClient(SESSION, API_ID, API_HASH).start(bot_token=BOT_TOKEN)

ALLOWED_USERS = AUTHORIZED_USERS_ID.replace(" ", "").split(",")

async def notify_users():
    if SEND_PUBLIC_IP.upper() == "TRUE":
        try:
            public_ip = requests.get("https://api.ipify.org").text
            message = f"The bot has started and is now online.\nPublic IP: {public_ip}"
            print(f"Bot on '{public_ip}'.") 
        except Exception as e:
            public_ip = "Could not retrieve IP"
            print(f"Error fetching public IP: {e}")
    else:
        message = "The bot has started and is now online."

    print(f"Bot started successfully.") 
    
    for user_id in ALLOWED_USERS:
        try:
            await client.send_message(int(user_id), message)
        except Exception as e:
            print(f"Failed to send start message to {user_id}: {e}")

@client.on(events.NewMessage(pattern='/showFolders'))
async def show_folders_handler(event):
    if str(event.chat_id) not in ALLOWED_USERS:
        await event.reply("You are not authorized to use this bot.")
        print(f"User {event.chat_id} not authorized.")
        return
    
    folders = [f for f in os.listdir(SEND_FILES_DIR) if os.path.isdir(os.path.join(SEND_FILES_DIR, f))]
    if not folders:
        await event.reply("No folders found in sendFiles directory.")
        return
    
    buttons = [Button.inline(folder, data=f"/folder:{folder}") for folder in folders]
    await event.reply("Select a folder:", buttons=buttons)

@client.on(events.CallbackQuery(pattern=r'^\/folder:'))
async def activate_deletion_callback_handler(event):
    await event.delete()
    if str(event.chat_id) not in ALLOWED_USERS:
        await event.answer("You are not authorized to use this bot.", alert=True)
        print(f"User {event.chat_id} not authorized.")
        return
    
    data = event.data.decode('utf-8')
    null, folder_name = data.split(":")
    folder_path = os.path.join(SEND_FILES_DIR, folder_name)
    
    if not os.path.exists(folder_path):
        await event.answer("Folder not found.", alert=True)
        return
    
    buttons = [
        Button.inline("Yes", data=f"/delete:{folder_name}"),
        Button.inline("No", data=f"/keep:{folder_name}")
    ]
    await client.send_message(event.chat_id, f"Do you want to delete the files in {folder_name} after sending?", buttons=buttons)

@client.on(events.CallbackQuery(pattern=r'^\/(delete|keep):'))
async def file_upload_callback_handler(event):
    if str(event.chat_id) not in ALLOWED_USERS:
        await event.answer("You are not authorized to use this bot.", alert=True)
        print(f"User {event.chat_id} not authorized.")
        await event.delete()
        return

    data = event.data.decode('utf-8')
    action, folder_name = data.split(":")
    delete_after_sending = False
    delete_message = ""
    if action == "/delete":
        delete_after_sending = True
        delete_message = " and deleting"

    folder_path = os.path.join(SEND_FILES_DIR, folder_name)
    
    files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not seven_zip_pattern.search(f)]
    if not files:
        await event.answer("No files found in the selected folder.", alert=True)
        await event.delete()
        return
    
    await event.delete()
    num_files = len(files)
    print(f"User {event.chat_id} is uploading{delete_message} {num_files} files from {folder_name}")
    message = await client.send_message(event.chat_id, f"Sending{delete_message} {num_files} files from {folder_name}")
    global progress_upload_message
    global current_file
    global chat_id
    chat_id = event.chat_id
    progress_upload_message = await client.send_message(event.chat_id, f"Loading files...")
    
    for file_path in sorted(files):
        file_size = os.path.getsize(file_path)
        if SEND_VIDEO_INFO.upper() == "TRUE":
            await client.send_message(chat_id, f"{file_path}\n{get_video_info(file_path)}")
        if file_size > 1.9 * 1024 * 1024 * 1024:  # If file is larger than 1.9GB
            await client.edit_message(event.chat_id, progress_upload_message, f"Splitting {file_path}")
            split_file(file_path)
            split_files = [f for f in os.listdir(folder_path) if f.startswith(os.path.basename(file_path)) and seven_zip_pattern.search(f)]
            num_files = num_files + len(split_files) - 1
            await client.edit_message(event.chat_id, message, f"Sending{delete_message} {num_files} files from {folder_name}")
            for split_file_path in sorted(split_files):
                current_file = split_file_path
                await client.edit_message(event.chat_id, progress_upload_message, f"Sending {current_file}")
                await client.send_file(event.chat_id, os.path.join(folder_path, split_file_path), force_document=True, progress_callback=upload_progress)
                if delete_after_sending:
                    delete_file(os.path.join(folder_path, split_file_path))  # Delete the split file
            if delete_after_sending:
                delete_file(file_path)  # Delete the original file before splitting
        else:
            current_file = file_path
            await client.edit_message(event.chat_id, progress_upload_message, f"Sending {current_file}")
            await client.send_file(event.chat_id, file_path, force_document=True, progress_callback=upload_progress)
            if delete_after_sending:
                delete_file(file_path)
    if delete_after_sending:
        delete_folder(folder_path)
    await client.edit_message(event.chat_id, progress_upload_message, f"All files sent.")
    print("All files sent.")
    await client.send_message(event.chat_id, "All files sent.")

def split_file(file_path):
    output_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    split_command = f'7z a -aoa -v1900M "{file_name}.7z" "{file_name}"'
    subprocess.call(split_command, shell=True, cwd=output_dir)

def delete_file(file_path):
    os.remove(file_path)

def delete_folder(folder_path):
    # Remove the Directory
    try: 
        os.rmdir(folder_path) 
        print(f"Directory '{folder_path}' has been removed successfully") 
    except OSError as error: 
        print(f"Directory '{folder_path}' can not be removed.\n{error}") 

async def upload_progress(current, total):
    global last_update_time
    
    if 'last_update_time' not in globals():
        last_update_time = 0
    
    current_time = asyncio.get_event_loop().time()
    if current_time - last_update_time >= UPDATE_UPLOAD_INTERVAL:
        last_update_time = current_time
        await client.edit_message(chat_id, progress_upload_message, f"Sending {current_file}\nProgress: {current/total:.2%}")

def get_video_info(file_path):
    # Run ffprobe to get stream info in JSON
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'stream', '-of', 'json', file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    probe_data = json.loads(result.stdout)

    video_stream = next((s for s in probe_data['streams'] if s['codec_type'] == 'video'), None)
    audio_streams = [s for s in probe_data['streams'] if s['codec_type'] == 'audio']
    subtitle_streams = [s for s in probe_data['streams'] if s['codec_type'] == 'subtitle']

    # Codec mapping to common names
    codec_map = {
        'h264': 'x264',
        'hevc': 'x265',
        'vp9': 'VP9',
        'av1': 'AV1',
        'mpeg4': 'MPEG-4',
        'vp8': 'VP8',
    }

    # Get resolution and codec
    if video_stream:
        width = video_stream.get('width', '?')
        height = video_stream.get('height', '?')
        codec_raw = video_stream.get('codec_name', 'unknown')
        codec = codec_map.get(codec_raw.lower(), codec_raw.upper())
        resolution = f"{width} x {height} ({codec})"
    else:
        resolution = "No video stream"

    def lang_to_emoji(lang_code, title=''):
        if not lang_code:
            return ''
        lang_code = lang_code.lower()
        title = (title or '').lower()
        # Special handling for Spanish
        if lang_code.startswith('spa') or lang_code.startswith('es'):
            if 'latin' in title:
                return flagz.by_code(lang_map_code.get('es-MX'))
            elif 'european' in title:
                return flagz.by_code(lang_map_code.get('es'))
            else:
                return flagz.by_code(lang_map_code.get('es'))
        country = lang_map_code.get(lang_code[:3], None)
        if country:
            return flagz.by_code(country)
        elif title:
            return title.capitalize()
        else:
            return f"🏳️({lang_code[:3]})"

    def unique_flags(streams):
        seen = set()
        flags = []
        for s in streams:
            lang = s.get('tags', {}).get('language', '')
            title = s.get('tags', {}).get('title', '')
            emoji = lang_to_emoji(lang, title)
            if emoji and emoji not in seen:
                seen.add(emoji)
                flags.append(emoji)
        return '+'.join(flags)

    audio_langs = unique_flags(audio_streams)
    subtitle_langs = unique_flags(subtitle_streams)

    if LANGUAGE_VIDEO_INFO.upper() == "ES":
        return f"Calidad: {resolution} \nAudio: {audio_langs or 'Ninguno'}\nSubtítulos: {subtitle_langs or 'Ninguno' }"
    else:
        return f"Quality: {resolution} \nAudio: {audio_langs or 'None'}\nSubtitles: {subtitle_langs or 'None'}"

with client:
    client.loop.run_until_complete(notify_users())
    client.run_until_disconnected()
