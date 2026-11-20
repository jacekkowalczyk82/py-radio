#!/usr/bin/env python3
"""Play radio stream URLs with VLC and record the listener's results."""

import argparse
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path


STATIONS = (
    ("Program 1", "https://stream11.polskieradio.pl/pr1/pr1.sdp/playlist.m3u8"),
    ("Program 2", "https://stream12.polskieradio.pl/pr2/pr2.sdp/playlist.m3u8"),
    ("Program 3", "https://stream13.polskieradio.pl/pr3/pr3.sdp/playlist.m3u8"),
    ("Eska Rock", "https://emsoft.ct8.pl/inne/time.m3u?id=5990"),
    ("Radio Niepokalanów (AAC)", "http://88.199.169.10:8004/listen.pls"),
    ("Radio Niepokalanów (MP3)", "http://88.199.169.10:8000/listen.pls"),
    ("Radio Parada", "http://stream4.nadaje.com:15274/live.m3u"),
    ("Radio Żak (OGG)", "http://www.radio.pionier.net.pl/stream.pls?radio=radiozak"),
    ("Radio Żak (MP3)", "http://ra.man.lodz.pl:8000/radiozak6.mp3.m3u"),
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Play each configured station with VLC and record whether you heard it."
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=20,
        help="seconds to play each station before asking for feedback (default: 20)",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path(__file__).with_name("test_stations.log"),
        help="file for prompts, answers, and test results",
    )
    parser.add_argument(
        "--vlc-log-file",
        type=Path,
        default=Path(__file__).with_name("test_stations_vlc.log"),
        help="file for VLC diagnostic output",
    )
    args = parser.parse_args()
    if args.duration < 1:
        parser.error("--duration must be at least 1 second")
    return args


def stop_player(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    args = parse_args()
    player = shutil.which("cvlc") or shutil.which("vlc")
    if not player:
        print("VLC was not found. Install VLC and make sure cvlc or vlc is on PATH.")
        return 2

    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    args.vlc_log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(args.log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger("station-test")
    results = []

    logger.info("Starting station test with %s; duration=%d seconds", player, args.duration)
    logger.info("VLC diagnostics are written to %s", args.vlc_log_file)

    try:
        for name, url in STATIONS:
            logger.info("Station: %s | URL: %s", name, url)
            logger.info("Starting playback for up to %d seconds.", args.duration)
            process = None

            try:
                with args.vlc_log_file.open("ab") as vlc_log:
                    vlc_log.write(f"\n--- {name}: {url} ---\n".encode("utf-8"))
                    vlc_log.flush()
                    process = subprocess.Popen(
                        [
                            player,
                            "--no-video",
                            "--no-one-instance",
                            "--verbose=2",
                            url,
                        ],
                        stdout=vlc_log,
                        stderr=subprocess.STDOUT,
                    )
                time.sleep(args.duration)
                if process.poll() is None:
                    logger.info("Playback process ran for the full test duration.")
                else:
                    logger.warning(
                        "VLC exited early with status %s; see the VLC log.",
                        process.returncode,
                    )
            except OSError:
                logger.exception("Could not start VLC for %s.", name)
                results.append((name, url, "ERROR: VLC did not start"))
                continue
            except KeyboardInterrupt:
                logger.info("Interrupted while playing %s.", name)
                stop_player(process)
                break
            finally:
                if process is not None:
                    stop_player(process)

            while True:
                prompt = f"Did you hear {name}? [y=yes / n=no / q=quit] "
                logger.info("PROMPT: %s", prompt.strip())
                try:
                    answer = input(prompt).strip().lower()
                except EOFError:
                    answer = "q"
                    print()
                logger.info("ANSWER: %s", answer or "<empty>")

                if answer in {"y", "yes", "n", "no", "q"}:
                    break
                print("Please enter y, n, or q.")

            if answer == "q":
                results.append((name, url, "QUIT before answer"))
                break

            result = "HEARD" if answer in {"y", "yes"} else "NOT HEARD"
            results.append((name, url, result))
            logger.info("RESULT: %s | %s", name, result)
    except KeyboardInterrupt:
        logger.info("Test interrupted.")

    logger.info("Station test summary:")
    for name, url, result in results:
        logger.info("SUMMARY: %s | %s | %s", name, result, url)
    logger.info("Full test log: %s", args.log_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
