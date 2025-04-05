# Telegram File Uploader

This is the code for a bot that will upload files on a folder to Telegram and delete them if the user wants to.

## How to use the bot

If you are one of the AUTHORIZED USERS set on the docker-compose.yml, you will be able to perform the following:

1. Send a `/showFolders`. You will get a replay showing all the folders on the upload directory as buttons.
2. Select the button corresponding to the folder you wish the bot to send.
3. Select whether you want the bot to delete the files after sending them.
4. Wait until all files are sent.

*Note: If the files are bigger than 2GB (the limit for a normal user), the bot will split the files in 1.9GB using 7z before sending them.*
*Note 2: The bot will not send 7z files that the program itself has not created.*

## How to install with docker

Create a docker-compose.yml file with the content of the one [on this repo](./docker-compose.yml). Then change the following environment options:

- `TG_API_ID` (MANDATORY): Telegram api id, can be obtained [here](https://my.telegram.org/auth?to=apps).
- `TG_API_HASH` (MANDATORY): Telegram api hash, can be obtained [here](https://my.telegram.org/auth?to=apps).
- `TG_BOT_TOKEN` (MANDATORY): Telegram bot token, can be created with the [BotFather](https://t.me/BotFather).
- `TG_BOT_TOKEN` (MANDATORY): Telegram chat ID or a list of IDs (separated with comma) of the users that are allow to interact with the bot. If you don't know how to get chat id send messages to him [@JsonDumpBot](https://t.me/JsonDumpBot).
- `TG_SESSION` (Optional - default: `uploader`): The file name of the session file to be used.
- `BOT_UPLOAD_DIR` (Optional - default: `/sendFiles`): The file path inside the container where the bot will look for folders to send files.
- `BOT_UPDATE_UPLOAD_INTERVAL` (Optional - default: `10`): The number of seconds the bot updates the message with the progress of each file is sent. NOTE: the lower the number the higher probability of the upload to fail due to many requests sent to Telegram.
- `SEND_PUBLIC_IP` (Optional - default: `False`): If this is True, the bot will send on the message its sends when it comes online the public IP it has.
- `SEND_VIDEO_INFO` (Optional - default: `False`): If this is True, the bot will send a message before each file the Quality and Code (eg: 1920 x 1080 (x264)). Also the Audio and Subtitle languages of the tracks as emojis.
- `LANGUAGE_VIDEO_INFO` (Optional - default: `EN`): It can be EN or ES and changes the language of the message that sends the video information.

After setting the environment values, change the volumes to correspond to the path you want the bot to access. The part on the left of the `:` is where the files are located on your machine. On the right is where the files will be inside the container, this must correspond to the path setted on `BOT_UPLOAD_DIR`. For example:

```yaml
volumes:
    - /tmp/files-to-send:/sendFiles
```
