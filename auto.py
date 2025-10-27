import json
import sys
import random
import time
from datetime import datetime
from http.client import HTTPSConnection

INFO_FILE = "info.txt"
MESSAGES_FILE = "messages.txt"
# Batas karakter standar Discord
DISCORD_MESSAGE_LIMIT = 2000

# --- Fungsi Utility ---

def get_timestamp():
    """
    Returns a timestamp in the format YYYY-MM-DD HH:MM:SS
    """
    return "[" + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "]"

# Fungsi sleep yang diperbaiki namanya dan memiliki nilai jitter default yang wajar
def safe_sleep(base_seconds, min_jitter, max_jitter):
    """
    Menyediakan jeda acak (jitter) untuk menghindari deteksi bot.
    """
    # Pastikan min_jitter selalu lebih kecil dari max_jitter
    jitter = random.randint(min_jitter, max_jitter)
    total_sleep = base_seconds + jitter
    print(f"{get_timestamp()} Sleeping for {total_sleep} seconds (base {base_seconds}s + jitter {jitter}s).")
    time.sleep(total_sleep)

# --- File I/O Functions (Perbaikan Encoding UTF-8) ---

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

# --- Configuration and Help Functions (Dibiarkan sama) ---

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
    # Perbaikan: Menggunakan domain Discord terbaru
    return HTTPSConnection("discord.com", 443)


def send_message(conn, channel_id, message_data, header_data):
    try:
        # Perbaikan: Menggunakan API v10
        conn.request("POST", f"/api/v10/channels/{channel_id}/messages", message_data, header_data)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="ignore")

        if 199 < resp.status < 300:
            # Perbaikan: Hanya menampilkan status sukses, bukan seluruh data pesan
            print(f"{get_timestamp()} Message sent! Status: {resp.status}")
            return True
        else:
            print(f"{get_timestamp()} Non-2xx response: {resp.status} - {body}")
            return False

    except Exception as e:
        print(f"{get_timestamp()} Error sending message: {e} | {message_data}")
        return False

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
        return

    header_data = {
        "Content-Type": "application/json",
        "User-Agent": info[0],  # Perbaikan: Menggunakan User-Agent
        "Authorization": info[1],
        "Host": "discord.com",
        "Referer": info[2]      # Perbaikan: Menggunakan Referer
    }

    print(f"{get_timestamp()} Messages will be sent to " + header_data["Referer"] + ".")

    print("Please initialise your delays and sleep time, there will be some random offsets applied as well!\n")
    # Perbaikan: Menggunakan nama variabel yang lebih jelas
    delay_between_chunks = int(input("Delay (in seconds) between messages/chunks (base): "))
    sleep_time_base = int(input("Sleep time (in seconds) between full cycles (base): "))

    while True:
        try:
            # Perbaikan: Ditambahkan encoding="utf-8"
            with open(MESSAGES_FILE, "r", encoding="utf-8") as file:
                messages = file.read().splitlines()
        except FileNotFoundError:
            print(f"{get_timestamp()} Messages file not found.")
            return

        for message in messages:
            if not message.strip():
                continue # Lewati baris kosong
            
            # Catatan: Karena Anda menggunakan splitlines(), jika pesan Anda ada di beberapa baris di messages.txt, 
            # skrip ini akan mengirim *semua* baris tersebut sebagai pesan terpisah dalam satu siklus.

            message_data = json.dumps({"content": message})
            conn = get_connection()
            send_message(conn, info[3], message_data, header_data)
            conn.close()

            # JEDA ANTAR PESAN/CHUNK: Menggunakan jitter kecil (1-10 detik)
            # Jika messages.txt hanya punya 1 baris, ini tidak akan terjadi (loop hanya 1x)
            # Jika messages.txt punya beberapa baris, ini adalah jeda antar baris.
            safe_sleep(delay_between_chunks, 1, 10) 

        print(f"{get_timestamp()} Finished sending all messages!")
        
        # JEDA ANTAR SIKLUS: Menggunakan sleep_time base (30 detik) dengan jitter 5-15 detik
        # Nilai jitter 20-1200 yang menyebabkan masalah telah DIHILANGKAN dan diganti dengan 5-15.
        print(f"{get_timestamp()} Initiating cycle sleep...")
        safe_sleep(sleep_time_base, 5, 15)


if __name__ == "__main__":
    main()
