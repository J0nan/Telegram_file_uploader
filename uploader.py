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
    null, folder_name = data.split(":", 1)
    folder_path = os.path.join(SEND_FILES_DIR, folder_name)
    
    if not os.path.exists(folder_path):
        await event.answer("Folder not found.", alert=True)
        return
    
    if TMDB_API_KEY:
        is_es = LANGUAGE_VIDEO_INFO.upper() == "ES"
        buttons = [
            Button.inline("Películas" if is_es else "Movies", data=f"/t:m:{folder_name}"),
            Button.inline("Series" if is_es else "TV Shows", data=f"/t:t:{folder_name}"),
            Button.inline("Ninguno" if is_es else "None", data=f"/t:n:{folder_name}")
        ]
        msg = "¿Qué tipo de contenido hay en esta carpeta?" if is_es else "What type of content is in this folder?"
        await client.send_message(event.chat_id, msg, buttons=buttons)
    else:
        buttons = [
            Button.inline("Yes", data=f"/do:d:n:{folder_name}"),
            Button.inline("No", data=f"/do:k:n:{folder_name}")
        ]
        await client.send_message(event.chat_id, f"Do you want to delete the files in {folder_name} after sending?", buttons=buttons)

@client.on(events.CallbackQuery(pattern=r'^\/t:'))
async def media_type_callback_handler(event):
    await event.delete()
    if str(event.chat_id) not in ALLOWED_USERS:
        return
    data = event.data.decode('utf-8')
    _, media_type, folder_name = data.split(":", 2)
    buttons = [
        Button.inline("Yes", data=f"/do:d:{media_type}:{folder_name}"),
        Button.inline("No", data=f"/do:k:{media_type}:{folder_name}")
    ]
    await client.send_message(event.chat_id, f"Do you want to delete the files in {folder_name} after sending?", buttons=buttons)

@client.on(events.CallbackQuery(pattern=r'^\/do:'))
async def file_upload_callback_handler(event):
    if str(event.chat_id) not in ALLOWED_USERS:
        await event.answer("You are not authorized to use this bot.", alert=True)
        print(f"User {event.chat_id} not authorized.")
        await event.delete()
        return

    data = event.data.decode('utf-8')
    _, action, media_type, folder_name = data.split(":", 3)
    delete_after_sending = False
    delete_message = ""
    if action == "d":
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
    
    failed_media = []

    # TMDB LOGIC
    if media_type == 'm': # Movies
        for file_path in sorted(files):
            file_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
            match = re.match(r'^(.*?)\s*(?:\((\d{4})\))?$', file_name_no_ext)
            if match:
                title, year = match.group(1), match.group(2)
                tmdb_res = search_tmdb_movie(title, year)
                if tmdb_res:
                    poster_url = f"https://image.tmdb.org/t/p/w500{tmdb_res.get('poster_path')}" if tmdb_res.get('poster_path') else None
                    overview = tmdb_res.get('overview', '')
                    vid_info = get_video_info(file_path) if SEND_VIDEO_INFO.upper() == "TRUE" else ""
                    
                    release_year = tmdb_res.get('release_date', '')[:4]
                    msg_text = f"{tmdb_res.get('title')} ({release_year})\n\n{overview}\n\n{vid_info}"
                    if poster_url:
                        await client.send_file(chat_id, poster_url, caption=msg_text)
                    else:
                        await client.send_message(chat_id, msg_text)
                else:
                    failed_media.append(f"Movie: {file_name_no_ext} (Not found in TMDB)")
                    continue # Skip sending this file
            else:
                failed_media.append(f"Movie: {file_name_no_ext} (Could not parse name/year)")
                continue

            await send_file_with_split(file_path, folder_path, delete_after_sending, message, folder_name)

    elif media_type == 't': # TV Shows
        series_groups = {}
        for file_path in files:
            file_name_no_ext = os.path.splitext(os.path.basename(file_path))[0]
            # Format: nombre - S01E01
            match = re.search(r'^(.*?)\s*-\s*[sS](\d+)[eE](\d+)', file_name_no_ext)
            if match:
                series_name = match.group(1).strip()
                # Clean year from series name if present (e.g. "The Rookie (2018)" -> "The Rookie")
                clean_name = re.sub(r'\s*\(\d{4}\)$', '', series_name).strip()
                season_num = int(match.group(2))
                
                if series_name not in series_groups:
                    series_groups[series_name] = {'clean_name': clean_name, 'seasons': {}}
                
                if season_num not in series_groups[series_name]['seasons']:
                    series_groups[series_name]['seasons'][season_num] = []
                
                series_groups[series_name]['seasons'][season_num].append(file_path)
            else:
                failed_media.append(f"File: {file_name_no_ext} (Doesn't match 'nombre - S01E01' format)")
                
        for series_name, series_data in series_groups.items():
            tmdb_series = search_tmdb_tv(series_data['clean_name'])
            if not tmdb_series:
                failed_media.append(f"Series: {series_name} (Not found in TMDB)")
                continue

            poster_url = f"https://image.tmdb.org/t/p/w500{tmdb_series.get('poster_path')}" if tmdb_series.get('poster_path') else None
            overview = tmdb_series.get('overview', '')
            release_year = tmdb_series.get('first_air_date', '')[:4]
            series_msg = f"{tmdb_series.get('name')} ({release_year})\n\n{overview}"
            
            if poster_url:
                await client.send_file(chat_id, poster_url, caption=series_msg)
            else:
                await client.send_message(chat_id, series_msg)
            
            series_id = tmdb_series.get('id')
            
            # Sort seasons
            for season_num in sorted(series_data['seasons'].keys()):
                season_files = sorted(series_data['seasons'][season_num])
                season_data = get_tmdb_tv_season(series_id, season_num)
                season_poster = f"https://image.tmdb.org/t/p/w500{season_data.get('poster_path')}" if season_data and season_data.get('poster_path') else None
                
                vid_info = get_video_info(season_files[0]) if SEND_VIDEO_INFO.upper() == "TRUE" else ""
                
                is_es = LANGUAGE_VIDEO_INFO.upper() == "ES"
                season_text = f"Temporada {season_num}\n{len(season_files)} episodios" if is_es else f"Season {season_num}\n{len(season_files)} episodes"
                season_msg = f"{season_text}\n\n{vid_info}"
                
                if season_poster:
                    await client.send_file(chat_id, season_poster, caption=season_msg)
                else:
                    await client.send_message(chat_id, season_msg)
                
                for file_path in season_files:
                    await send_file_with_split(file_path, folder_path, delete_after_sending, message, folder_name)

    else: # None / Default
        for file_path in sorted(files):
            if SEND_VIDEO_INFO.upper() == "TRUE":
                await client.send_message(chat_id, f"{file_path}\n{get_video_info(file_path)}")
            await send_file_with_split(file_path, folder_path, delete_after_sending, message, folder_name)

    if delete_after_sending and not failed_media:
        # Only delete folder if everything was sent successfully
        delete_folder(folder_path)
        
    await client.edit_message(event.chat_id, progress_upload_message, f"All files sent.")
    print("All files sent.")
    
    if failed_media:
        fail_msg = "The following media failed to upload due to TMDB lookup or parsing errors:\n" + "\n".join(failed_media)
        await client.send_message(event.chat_id, fail_msg)
    else:
        await client.send_message(event.chat_id, "All files sent.")

async def send_file_with_split(file_path, folder_path, delete_after_sending, message, folder_name):
    global current_file
    file_size = os.path.getsize(file_path)
    if file_size > 1.9 * 1024 * 1024 * 1024:
        await client.edit_message(chat_id, progress_upload_message, f"Splitting {file_path}")
        split_file(file_path)
        split_files = [f for f in os.listdir(folder_path) if f.startswith(os.path.basename(file_path)) and seven_zip_pattern.search(f)]
        for split_file_path in sorted(split_files):
            current_file = split_file_path
            await client.edit_message(chat_id, progress_upload_message, f"Sending {current_file}")
            await client.send_file(chat_id, os.path.join(folder_path, split_file_path), force_document=True, progress_callback=upload_progress)
            if delete_after_sending:
                delete_file(os.path.join(folder_path, split_file_path))
        if delete_after_sending:
            delete_file(file_path)
    else:
        current_file = file_path
        await client.edit_message(chat_id, progress_upload_message, f"Sending {current_file}")
        await client.send_file(chat_id, file_path, force_document=True, progress_callback=upload_progress)
        if delete_after_sending:
            delete_file(file_path)

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
            return f"{title.capitalize()}({lang_code[:3]})"
            # return title.capitalize()
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

def tmdb_request(url, params):
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"TMDB request failed: {e}")
    return None

def search_tmdb_movie(name, year=None):
    lang = "es-ES" if LANGUAGE_VIDEO_INFO.upper() == "ES" else "en-US"
    params = {'api_key': TMDB_API_KEY, 'query': name, 'language': lang}
    if year:
        params['primary_release_year'] = year
    res = tmdb_request("https://api.themoviedb.org/3/search/movie", params)
    if res and res.get('results'):
        return res['results'][0]
    return None

def search_tmdb_tv(name):
    lang = "es-ES" if LANGUAGE_VIDEO_INFO.upper() == "ES" else "en-US"
    params = {'api_key': TMDB_API_KEY, 'query': name, 'language': lang}
    res = tmdb_request("https://api.themoviedb.org/3/search/tv", params)
    if res and res.get('results'):
        return res['results'][0]
    return None

def get_tmdb_tv_season(series_id, season_number):
    lang = "es-ES" if LANGUAGE_VIDEO_INFO.upper() == "ES" else "en-US"
    params = {'api_key': TMDB_API_KEY, 'language': lang}
    return tmdb_request(f"https://api.themoviedb.org/3/tv/{series_id}/season/{season_number}", params)

with client:
    client.loop.run_until_complete(notify_users())
    client.run_until_disconnected()
