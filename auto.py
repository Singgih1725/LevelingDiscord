import json
import sys
import random
import time
from datetime import datetime
from http.client import HTTPSConnection

INFO_FILE = "info.txt"
MESSAGES_FILE = "messages.txt"
# Batas karakter per pesan Discord. Tidak ada di skrip asli Anda, tapi ini adalah batasnya.
DISCORD_MESSAGE_LIMIT = 2000


def get_timestamp():
    """
    Returns a timestamp in the format YYYY-MM-DD HH:MM:SS
    """
    return "[" + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "]"


def safe_sleep(base_seconds, min_jitter=5, max_jitter=15):
    """
    Menyediakan jeda acak untuk menghindari deteksi bot.
    """
    jitter = random.randint(min_jitter, max_jitter)
    total_sleep = base_seconds + jitter
    print(f"{get_timestamp()} Sleeping for {total_sleep} seconds (base {base_seconds}s + jitter {jitter}s).")
    time.sleep(total_sleep)


# --- File I/O Functions ---

def read_info():
    try:
        # Ditambahkan encoding="utf-8"
        with open(INFO_FILE, "r", encoding="utf-8") as file:
            return file.read().splitlines()
    except FileNotFoundError:
        print(f"{get_timestamp()} Info file not found.")
        return None


def write_info(user_id, token, channel_url, channel_id):
    try:
        # Ditambahkan encoding="utf-8"
        with open(INFO_FILE, "w", encoding="utf-8") as file:
            file.write(f"{user_id}\n{token}\n{channel_url}\n{channel_id}")
    except Exception as e:
        print(f"{get_timestamp()} Error configuring user information: {e}")
        exit()


# --- Configuration and Help Functions (Unchanged) ---

def configure_info():
    try:
        user_id = input("User-ID: ")
        token = input("Discord token: ")
        channel_url = input("Discord channel URL: ")
        channel_id = input("Discord channel ID: ")
        write_info(user_id, token, channel_url, channel_id)
        print(f"Written config to info.txt, please rerun to start!")
    except Exception as e:
        print(f"{get_timestamp()} Error configuring user information: {e}")
        exit()


def set_channel():
    info = read_info()
    if info:
        user_id, token, _, _ = info
        channel_url = input("Discord channel URL: ")
        channel_id = input("Discord channel ID: ")
        write_info(user_id, token, channel_url, channel_id)
        print(f"Written config to info.txt, please rerun to start!")


def show_help():
    print("Showing help for discord-auto-messenger")
    print("Usage:")
    print("  'python3 auto.py'           : Runs the automessenger. Type in the wait time and take a back seat.")
    print("  'python3 auto.py --config'  : Configure settings.")
    print("  'python3 auto.py --setC'    : Set channel to send message to. Including Channel ID and Channel URL")
    print("  'python3 auto.py --help'    : Show help")


# --- Discord API Functions ---

def get_connection():
    # Perbaiki domain dari discordapp.com (lama) menjadi discord.com (baru) dan API v10
    return HTTPSConnection("discord.com", 443)


def send_message(conn, channel_id, message_data, header_data):
    try:
        # Perbaiki endpoint dari /api/v6 (lama) menjadi /api/v10 (baru)
        conn.request("POST", f"/api/v10/channels/{channel_id}/messages", message_data, header_data)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="ignore")
        
        if 199 < resp.status < 300:
            print(f"{get_timestamp()} Message sent! Status: {resp.status}")
        else:
            # Tambahkan penanganan Rate Limit (429) sederhana
            print(f"{get_timestamp()} Non-2xx response: {resp.status} - {body}")

    except Exception as e:
        print(f"{get_timestamp()} Error sending message: {e} | {message_data}")


# --- Main Logic ---

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--config" and input("Configure? (y/n) ") == "y":
            configure_info()
            return
        elif sys.argv[1] == "--setC" and input("Set channel? (y/n) ") == "y":
            set_channel()
            return
        elif sys.argv[1] == "--help":
            show_help()
            return

    info = read_info()
    if not info or len(info) != 4:
        print(
            f"{get_timestamp()} An error was found inside the user information file. Please ensure the file contains "
            f"the following information in order: User agent, Discord token, Discord channel URL, and Discord channel "
            f"ID. Try again with python3 auto.py --config"
        )
        # Hentikan atau konfigurasi ulang jika file info tidak ada
        if not info:
             configure_info()
        return

    header_data = {
        "Content-Type": "application/json",
        "User-Agent": info[0], # Ganti User-ID menjadi User-Agent untuk kepatuhan API
        "Authorization": info[1],
        "Host": "discord.com",
        "Referer": info[2] # Ganti referrer menjadi Referer
    }

    print(f"{get_timestamp()} Messages will be sent to " + header_data["Referer"] + ".")

    print("Set delays: (Delay antar pesan/chunk disarankan kecil. Sleep time adalah jeda antar-siklus.)\n")
    # Jeda antar pesan/chunk diatur kecil untuk pesan panjang
    delay_between_messages = int(input("Delay base (in seconds) between messages/chunks (base, jitter akan ditambahkan kecil): "))
    # Jeda utama antar-siklus diatur 30 detik
    sleep_time = int(input("Sleep time (in seconds) between full cycles (base, jitter akan ditambahkan besar): "))

    while True:
        try:
            # Ditambahkan encoding="utf-8" untuk dukungan emoji/unicode
            with open(MESSAGES_FILE, "r", encoding="utf-8") as file:
                # Menggunakan read() untuk seluruh konten karena pesan Anda satu kesatuan
                message_content = file.read() 
        except FileNotFoundError:
            print(f"{get_timestamp()} Messages file not found.")
            return

        # Skrip ini tidak memiliki fungsi 'chunk_text' yang Anda gunakan di pertanyaan sebelumnya, 
        # sehingga hanya akan mengirim seluruh konten sebagai satu pesan (selama < 2000 kar.)
        if message_content and len(message_content) <= DISCORD_MESSAGE_LIMIT:
            
            message_data = json.dumps({"content": message_content})
            conn = get_connection()
            send_message(conn, info[3], message_data, header_data)
            conn.close()
            
            # Catatan: Karena pesan Anda hanya 1, delay_between_messages tidak digunakan.

            print(f"{get_timestamp()} Finished sending message(s) for this cycle.")
            
        elif len(message_content) > DISCORD_MESSAGE_LIMIT:
             print(f"{get_timestamp()} ERROR: Message content exceeds {DISCORD_MESSAGE_LIMIT} characters and chunking logic is missing.")

        else:
             print(f"{get_timestamp()} No message content found in {MESSAGES_FILE}.")
        
        # Jeda utama antar siklus. Jitter (5-15 detik) ditambahkan di fungsi safe_sleep.
        safe_sleep(sleep_time, 5, 15)


if __name__ == "__main__":
    main()
