import requests
import time
import json
import subprocess
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import signal
import sys
import re

# Telegram Bot Token
BOT_TOKEN = os.getenv('bttkn')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'

# State management for users
user_states = defaultdict(lambda: {'state': None, 'url_template': None, 'start_num': None})
user_file_types = defaultdict(lambda: 'document')  # Default file type is document

# Lock for thread-safe operations
lock = threading.Lock()

# Track active users and rate limits
active_users = 0  # Count of active users
max_files_per_minute = 19  # Limit of files sent per minute
time_per_request = 3  # Approximate time taken for each request in seconds

# Thread pool for concurrent user handling
executor = ThreadPoolExecutor(max_workers=20)  # Adjust based on your server capacity


# Function to get updates from Telegram
def get_updates(offset=None):
    url = f"{TELEGRAM_API_URL}/getUpdates?timeout=100"
    if offset:
        url += f"&offset={offset}"
    response = requests.get(url)
    return response.json()



def extract_links(text):
    """
    Extract all URLs from a given text.
    """
    url_pattern = r"(https?://[^\s]+)"
    return re.findall(url_pattern, text)

# Function to send a message back to the chat
def send_message(chat_id, text):
    params = {'chat_id': chat_id, 'text': text}
    response = requests.get(f"{TELEGRAM_API_URL}/sendMessage", params=params)
    if response.status_code == 429:  # Too Many Requests
        retry_after = int(response.headers.get('Retry-After', 1))
        time.sleep(retry_after)
        send_message(chat_id, text)
    return response


# Generate URLs based on user input
def generate_custom_urls(url_template, start_num, end_num):
    urls = [url_template.replace('*', str(i)) for i in range(start_num, end_num + 1)]
    return urls


# Send the file to the user's chat using the specified file type
def send_file_to_user(chat_id, file_url, file_type='document'):
    params = {'chat_id': chat_id}
    # Create the inline keyboard
    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "🔄 Download Again",
                    "url": file_url
                }
            ]
        ]
    }
    params['reply_markup'] = json.dumps(reply_markup)

    if file_type == 'document':
        params['document'] = file_url
        response = requests.get(f'{TELEGRAM_API_URL}/sendDocument', params=params)
    elif file_type == 'photo':
        params['photo'] = file_url
        response = requests.get(f'{TELEGRAM_API_URL}/sendPhoto', params=params)
    elif file_type == 'audio':
        params['audio'] = file_url
        response = requests.get(f'{TELEGRAM_API_URL}/sendAudio', params=params)
    elif file_type == 'video':
        params['video'] = file_url
        response = requests.get(f'{TELEGRAM_API_URL}/sendVideo', params=params)

    if response.status_code == 200:
        print(f"Successfully sent: {file_url}")
        return True
    else:
        print(f"Failed to send {file_url}, Status Code: {response.status_code}, Error: {response.json().get('description')}")
        return False


# Handle the /godmode command
def handle_godmode(chat_id):
    if user_states[chat_id]['state'] is None:  # Check if the user is already in a state
        send_message(chat_id, "Activating god mode...")
        send_message(chat_id, "Enter the URL template (use * as a placeholder):")
        user_states[chat_id]['state'] = 'waiting_for_template'
    else:
        send_message(chat_id, "You are already in god mode. Please complete your current task.")


# Function to display bot info
def display_info(chat_id):
    info_text = (
        "Welcome to the File Sender Bot!\n\n"
        "☼ Use the /godmode command to generate custom URLs and send documents.\n"
        "☼ Use /settings to choose the file type for sending files."
    )
    send_message(chat_id, info_text)


# Handle user settings
def handle_settings(chat_id):
    settings_text = (
        "Choose a file type for sending files:\n"
        "/document - Send as document\n"
        "/photo - Send as photo\n"
        "/video - Send as video\n"
        "/audio - Send as audio\n"
        "Please type the command you want to set as your default file type."
    )
    send_message(chat_id, settings_text)


# Thread-safe increment/decrement of active users
def increment_active_users():
    global active_users
    with lock:
        active_users += 1


def decrement_active_users():
    global active_users
    with lock:
        active_users -= 1


# Handle user request logic
import instaloader
import subprocess
import os
import time

# Function to get Instagram video URL using Instaloader
# Function to get Instagram video URL using yt-dlp
def get_instagram_video_url(url):
    try:
        # Use yt-dlp to fetch the video URL
        command = ["yt-dlp", "--cookies-from-browser", "chrome", "-g", url]
        process = subprocess.run(command, capture_output=True, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

        if process.returncode == 0:
            # Extracted video URL
            return process.stdout.strip()
        else:
            # If yt-dlp fails, return an error message
            return None
    except FileNotFoundError:
        return "yt-dlp is not installed."
    except Exception as e:
        return f"Error fetching Instagram video with yt-dlp: {str(e)}"


def handle_user_request(chat_id, message_text):
    increment_active_users()
    try:
        user_state = user_states.get(chat_id, {})

        # Handle user states
        if user_state.get('state') == 'waiting_for_template':
            user_state['url_template'] = message_text
            user_state['state'] = 'waiting_for_start_num'
            send_message(chat_id, "Enter the starting number:")

        elif user_state.get('state') == 'waiting_for_start_num':
            try:
                user_state['start_num'] = int(message_text)
                user_state['state'] = 'waiting_for_end_num'
                send_message(chat_id, "Enter the ending number:")
            except ValueError:
                send_message(chat_id, "Please enter a valid integer for the starting number.")

        elif user_state.get('state') == 'waiting_for_end_num':
            try:
                end_num = int(message_text)
                if user_state.get('url_template'):
                    urls = generate_custom_urls(user_state['url_template'], user_state['start_num'], end_num)
                    sent_count = 0
                    start_time = time.time()

                    for url in urls:
                        file_type = user_file_types.get(chat_id, 'video')  # Default to video if not set
                        if send_file_to_user(chat_id, url, file_type):
                            sent_count += 1

                        if sent_count >= max_files_per_minute:
                            elapsed_time = time.time() - start_time
                            if elapsed_time < 60:
                                time.sleep(60 - elapsed_time)
                            start_time = time.time()
                            sent_count = 0

                    user_states[chat_id] = {'state': None, 'url_template': None, 'start_num': None}  # Reset state
                else:
                    send_message(chat_id, "URL template not set. Please start by providing the template.")
            except ValueError:
                send_message(chat_id, "Please enter a valid integer for the ending number.")

        else:  # If no state, handle commands
            if message_text == "/start":
                display_info(chat_id)
            elif message_text == "/settings":
                handle_settings(chat_id)
            elif message_text in ["/document", "/photo", "/video", "/audio"]:
                user_file_types[chat_id] = message_text[1:]  # Extract file type
                send_message(chat_id, f"File type set to send as {message_text[1:]}.")
            elif message_text == "/godmode":
                handle_godmode(chat_id)
            elif message_text.startswith("/chk"):
                try:
                    url = message_text[5:].strip()
                    if not url:
                        send_message(chat_id, "Please provide a valid URL.")
                        return

                    command = ["yt-dlp", "--cookies-from-browser", "chrome", "-g", url]
                    process = subprocess.run(command, capture_output=True, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

                    final_url = process.stdout.strip() if process.returncode == 0 else None
                    send_message(chat_id, final_url or f"Failed to process the video link. Error: {process.stderr.strip()}")
                except FileNotFoundError:
                    send_message(chat_id, "yt-dlp is not installed.")
                except Exception as e:
                    send_message(chat_id, f"An error occurred: {e}")
           
            else:
    # Extract all URLs from the message
                urls = extract_links(message_text)

                if urls:
                    for url in urls:
                        if "instagram.com" in url:
                # Use Instaloader to handle Instagram URL
                            video_url = get_instagram_video_url(url)
                            if video_url:
                                send_file_to_user(chat_id, video_url, user_file_types.get(chat_id, 'document'))
                            else:
                                send_message(chat_id, f"Failed to fetch Instagram video: {url}")
                        elif ("youtube.com" in url or "youtu.be" in url or "facebook.com" in url):
                            try:
                    # For YouTube or other video links, use yt-dlp
                                command = ["yt-dlp", "--cookies-from-browser", "chrome", "-g", url]
                                process = subprocess.run(command, capture_output=True, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                                if process.returncode == 0:
                                    final_url = process.stdout.strip()
                                    send_file_to_user(chat_id, final_url, user_file_types.get(chat_id, 'video'))
                                else:
                                    send_message(chat_id, f"Failed to process the video link: {url}")
                            except Exception as e:
                                send_message(chat_id, f"An error occurred while processing {url}: {str(e)}")
            
                        elif url.startswith("http://") or url.startswith("https://"):
                            send_file_to_user(chat_id, url, user_file_types.get(chat_id, 'video'))
                        else:
                            send_message(chat_id, f"Unsupported URL: {url}")
                else:
                    send_message(chat_id, "No valid URLs found in your message.")


    finally:
        decrement_active_users()

# Main polling loop
def main():
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        for update in updates.get('result', []):
            if 'message' in update and 'text' in update['message']:
                chat_id = update['message']['chat']['id']
                message_text = update['message']['text']
                executor.submit(handle_user_request, chat_id, message_text)
                last_update_id = update['update_id'] + 1


if __name__ == "__main__":
    main()
