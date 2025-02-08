from urllib.parse import urlparse
import datetime
import telebot
import yt_dlp
import re
import os
import time
from telebot import types
from telebot.util import quick_markup
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get variables from environment
bot_token = os.getenv("bot_token")
logs = os.getenv("logs")
max_filesize = int(os.getenv("max_filesize", "50000000"))  # Default 50MB

# Initialize bot
bot = telebot.TeleBot(bot_token)
last_edited = {}

def youtube_url_validation(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return re.match(youtube_regex, url)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message, "*Send me a video link* and I'll download it for you.\n\n"
                 "_Supported: YouTube, Twitter, TikTok, Reddit & more_\n\n"
                 "_Powered by_ [yt-dlp](https://github.com/yt-dlp/yt-dlp/)",
        parse_mode="MARKDOWN", disable_web_page_preview=True)

def download_video(message, url, audio=False, format_id="mp4"):
    if not urlparse(url).scheme:
        bot.reply_to(message, 'Invalid URL')
        return

    if "youtube" in url or "youtu.be" in url:
        if not youtube_url_validation(url):
            bot.reply_to(message, 'Invalid YouTube URL')
            return

    def progress(d):
        if d['status'] == 'downloading':
            try:
                update = False
                if last_edited.get(f"{message.chat.id}-{msg.message_id}"):
                    if (datetime.datetime.now() - last_edited[f"{message.chat.id}-{msg.message_id}"]).total_seconds() >= 5:
                        update = True
                else:
                    update = True
                
                if update:
                    perc = round(d['downloaded_bytes'] * 100 / d['total_bytes'])
                    bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=f"Downloading: {d['info_dict']['title']}\n\n{perc}%")
                    last_edited[f"{message.chat.id}-{msg.message_id}"] = datetime.datetime.now()
            except Exception as e:
                print(e)

    msg = bot.reply_to(message, 'Downloading...')
    video_title = round(time.time() * 1000)

    ydl_opts = {
        'format': format_id,
        'outtmpl': f'outputs/{video_title}.%(ext)s',
        'progress_hooks': [progress],
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}] if audio else [],
        'max_filesize': max_filesize
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text='Sending file to Telegram...')
            file_path = info['requested_downloads'][0]['filepath']
            
            try:
                if audio:
                    bot.send_audio(message.chat.id, open(file_path, 'rb'), reply_to_message_id=message.message_id)
                else:
                    width, height = info['requested_downloads'][0]['width'], info['requested_downloads'][0]['height']
                    bot.send_video(message.chat.id, open(file_path, 'rb'), reply_to_message_id=message.message_id, width=width, height=height)
                bot.delete_message(message.chat.id, msg.message_id)
            except Exception:
                bot.edit_message_text(
                    chat_id=message.chat.id, message_id=msg.message_id,
                    text=f"Couldn't send file. Make sure it's supported by Telegram and doesn't exceed *{round(max_filesize / 1000000)}MB*",
                    parse_mode="MARKDOWN")
        except yt_dlp.utils.DownloadError:
            bot.edit_message_text('Invalid URL', message.chat.id, msg.message_id)
        except Exception:
            bot.edit_message_text(
                f"Error downloading video. Ensure it doesn't exceed *{round(max_filesize / 1000000)}MB*",
                message.chat.id, msg.message_id, parse_mode="MARKDOWN")

        for file in os.listdir('outputs'):
            if file.startswith(str(video_title)):
                os.remove(f'outputs/{file}')

def log(message, text: str, media: str):
    if logs:
        chat_info = "Private chat" if message.chat.type == 'private' else f"Group: *{message.chat.title}* (`{message.chat.id}`)"
        bot.send_message(logs, f"Download request ({media}) from @{message.from_user.username} ({message.from_user.id})\n\n{chat_info}\n\n{text}")

def get_text(message):
    if len(message.text.split(' ')) < 2:
        return message.reply_to_message.text if message.reply_to_message and message.reply_to_message.text else None
    return message.text.split(' ')[1]

@bot.message_handler(commands=['download'])
def download_command(message):
    text = get_text(message)
    if not text:
        bot.reply_to(message, 'Invalid usage, use `/download url`', parse_mode="MARKDOWN")
        return
    log(message, text, 'video')
    download_video(message, text)

@bot.message_handler(commands=['audio'])
def download_audio_command(message):
    text = get_text(message)
    if not text:
        bot.reply_to(message, 'Invalid usage, use `/audio url`', parse_mode="MARKDOWN")
        return
    log(message, text, 'audio')
    download_video(message, text, True)

@bot.message_handler(commands=['custom'])
def custom(message):
    text = get_text(message)
    if not text:
        bot.reply_to(message, 'Invalid usage, use `/custom url`', parse_mode="MARKDOWN")
        return

    msg = bot.reply_to(message, 'Getting formats...')
    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(text, download=False)

    data = {f"{x['resolution']}.{x['ext']}": {'callback_data': f"{x['format_id']}"} for x in info['formats'] if x['video_ext'] != 'none'}
    markup = quick_markup(data, row_width=2)

    bot.delete_message(msg.chat.id, msg.message_id)
    bot.reply_to(message, "Choose a format", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.from_user.id == call.message.reply_to_message.from_user.id:
        url = get_text(call.message.reply_to_message)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        download_video(call.message.reply_to_message, url, format_id=f"{call.data}+bestaudio")
    else:
        bot.answer_callback_query(call.id, "You didn't send the request")

@bot.message_handler(func=lambda m: True)
def handle_private_messages(message):
    text = message.text if message.text else message.caption if message.caption else None
    if message.chat.type == 'private':
        log(message, text, 'video')
        download_video(message, text)

bot.infinity_polling()
