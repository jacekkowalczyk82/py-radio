import os
import json
import logging
import boto3
import re
import subprocess
import threading
import uuid
from flask import Flask, render_template, request, jsonify
from urllib.parse import parse_qs, urlparse

import sys
from configparser import ConfigParser

# Add parent directory to path to import messaging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from messaging import MessagingFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebControl")

def read_config():
    config_path = os.path.expanduser("~/.config/py-radio/config.ini")
    logger.info(f"Reading config from {config_path}")
    
    config_parser = ConfigParser()
    config_parser.read(config_path)
    
    config = dict(config_parser["default"]) if "default" in config_parser else {}
    
    if "aws" in config_parser.sections():
        config.update(config_parser["aws"])
        
    if "rabbitmq" in config_parser.sections():
        config.update(config_parser["rabbitmq"])

    if "mqtt" in config_parser.sections():
        config.update(config_parser["mqtt"])
        
    return config

# Load config once at startup
CONFIG = read_config()

app = Flask(__name__)

playlist_jobs = {}
playlist_jobs_lock = threading.Lock()

def send_message(action, station_name=None, station_url=None, volume=100):
    producer = MessagingFactory.get_producer(CONFIG)
    return producer.send_message(action, station_name, station_url, volume)

def create_playlist_file(playlist_url, playlist_name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", playlist_name):
        raise ValueError("Playlist name must contain only letters, numbers, underscores, and hyphens.")

    parsed_url = urlparse(playlist_url)
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in {"youtube.com", "www.youtube.com", "music.youtube.com"}
        or parsed_url.path != "/playlist"
        or not parse_qs(parsed_url.query).get("list")
    ):
        raise ValueError("Enter a YouTube playlist URL.")

    temp_dir = os.path.abspath(os.path.expanduser(os.path.join(
        "~", CONFIG.get("playtube.home.temp", "private/music/youtube-dl-temp")
    )))
    os.makedirs(temp_dir, exist_ok=True)

    filename_result = subprocess.run(
        ["yt-dlp", "-f", "ba", "--get-filename", "--restrict-filenames", playlist_url],
        cwd=temp_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if filename_result.returncode:
        raise RuntimeError(filename_result.stderr.strip() or "Could not read playlist filenames.")

    filenames = [line.strip() for line in filename_result.stdout.splitlines() if line.strip()]
    if not filenames:
        raise RuntimeError("The playlist did not contain any downloadable audio.")

    download_result = subprocess.run(
        ["yt-dlp", "-f", "ba", "--restrict-filenames", playlist_url],
        cwd=temp_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if download_result.returncode:
        raise RuntimeError(download_result.stderr.strip() or "Playlist download failed.")

    audio_files = []
    for filename in filenames:
        exact_path = os.path.join(temp_dir, filename)
        if os.path.isfile(exact_path):
            audio_files.append(exact_path)
            continue

        base_name, _ = os.path.splitext(filename)
        matching_paths = sorted(
            os.path.join(temp_dir, candidate)
            for candidate in os.listdir(temp_dir)
            if candidate.startswith(base_name + ".")
            and os.path.isfile(os.path.join(temp_dir, candidate))
        )
        audio_files.extend(matching_paths)

    if not audio_files:
        raise RuntimeError("Download finished, but no playlist audio files were found.")

    music_dir = os.path.expanduser("~/Music")
    os.makedirs(music_dir, exist_ok=True)
    playlist_path = os.path.join(music_dir, f"{playlist_name}.txt")
    temporary_path = f"{playlist_path}.{uuid.uuid4().hex}.tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as playlist_file:
            playlist_file.write(f"{playlist_url}\n")
            for audio_path in dict.fromkeys(audio_files):
                playlist_file.write(f"{audio_path}\n")
        os.replace(temporary_path, playlist_path)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)

    return playlist_path, len(set(audio_files))

def run_playlist_job(job_id, playlist_url, playlist_name):
    try:
        with playlist_jobs_lock:
            playlist_jobs[job_id]["message"] = "Reading playlist and downloading missing files..."
        playlist_path, file_count = create_playlist_file(playlist_url, playlist_name)
        with playlist_jobs_lock:
            playlist_jobs[job_id].update(
                status="complete",
                message=f"Playlist updated with {file_count} audio files.",
                path=playlist_path,
            )
    except (OSError, RuntimeError, ValueError) as error:
        logger.exception("Playlist update failed")
        with playlist_jobs_lock:
            playlist_jobs[job_id].update(status="error", message=str(error))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/playlists', methods=['POST'])
def create_playlist():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "A JSON request is required."}), 400

    playlist_url = data.get("url", "").strip()
    playlist_name = data.get("name", "").strip()
    if not playlist_url or not playlist_name:
        return jsonify({"status": "error", "message": "Playlist URL and name are required."}), 400
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", playlist_name):
        return jsonify({"status": "error", "message": "Use only letters, numbers, underscores, and hyphens for the playlist name."}), 400

    parsed_url = urlparse(playlist_url)
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in {"youtube.com", "www.youtube.com", "music.youtube.com"}
        or parsed_url.path != "/playlist"
        or not parse_qs(parsed_url.query).get("list")
    ):
        return jsonify({"status": "error", "message": "Enter a YouTube playlist URL."}), 400

    job_id = uuid.uuid4().hex
    with playlist_jobs_lock:
        playlist_jobs[job_id] = {"status": "running", "message": "Starting playlist update..."}
    threading.Thread(
        target=run_playlist_job,
        args=(job_id, playlist_url, playlist_name),
        daemon=True,
        name=f"playlist-update-{job_id[:8]}",
    ).start()
    return jsonify({"job_id": job_id, "status": "running"}), 202

@app.route('/api/playlists/<job_id>', methods=['GET'])
def playlist_job_status(job_id):
    with playlist_jobs_lock:
        job = playlist_jobs.get(job_id)
        if job is None:
            return jsonify({"status": "error", "message": "Playlist job not found."}), 404
        return jsonify(job)

@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    action = data.get('action')
    station_name = data.get('name')
    station_url = data.get('station')
    volume = data.get('volume', 100)
    
    if not action:
        return jsonify({"status": "error", "message": "Action is required"}), 400
        
    success, result = send_message(action, station_name, station_url, volume)
    
    if success:
        return jsonify({"status": "success", "message_id": result}), 200
    else:
        return jsonify({"status": "error", "message": result}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
