#!/usr/bin/env python3
"""Play radio streams using the python-vlc API and record listener feedback."""

import argparse
import logging
import sys
import time
from pathlib import Path


STATIONS = (
    ("Eska Rock (MP3)", "http://ic1.smcdn.pl/5990-1.mp3"),
    ("Radio Parada", "http://stream4.nadaje.com:15274/live"),
    ("Radio Żak (OGG)", "http://poznan2.radio.pionier.net.pl:8000/pl/radiozak.ogg"),
    ("Radio Żak (MP3)", "http://ra.man.lodz.pl:8000/radiozak6.mp3"),
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Play each station using python-vlc and record whether it was heard."
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
        default=Path(__file__).with_name("test_stations_vlc_api.log"),
        help="file for prompts, answers, and playback state diagnostics",
    )
    args = parser.parse_args()
    if args.duration < 1:
        parser.error("--duration must be at least 1 second")
    return args


def ask_listener(logger, station_name):
    while True:
        prompt = f"Did you hear {station_name}? [y=yes / n=no / q=quit] "
        logger.info("PROMPT: %s", prompt.strip())
        try:
            answer = input(prompt).strip().lower()
        except EOFError:
            answer = "q"
            print()

        logger.info("ANSWER: %s", answer or "<empty>")
        if answer in {"y", "yes", "n", "no", "q"}:
            return answer
        print("Please enter y, n, or q.")


def play_station(vlc, player, media, name, url, duration, logger):
    player.set_media(media)
    logger.info("Starting playback: %s | %s", name, url)
    if player.play() == -1:
        logger.error("VLC failed to start playback for %s.", name)
        return "PLAY ERROR"

    deadline = time.monotonic() + duration
    last_state = None
    while time.monotonic() < deadline:
        state = player.get_state()
        if state != last_state:
            logger.info("VLC state for %s: %s", name, state)
            last_state = state
        if state == vlc.State.Error:
            logger.error("VLC reported an error while playing %s.", name)
            return "VLC ERROR"
        if state == vlc.State.Ended:
            logger.warning("VLC reached end of media before the test duration: %s.", name)
            return "ENDED EARLY"
        time.sleep(0.25)

    state = player.get_state()
    logger.info("Playback window finished for %s; final VLC state: %s", name, state)
    return "PLAYED"


def main():
    args = parse_args()
    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(args.log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger("station-test-vlc-api")

    try:
        import vlc
    except ImportError:
        logger.exception("python-vlc is not installed in this Python environment.")
        return 2

    instance = None
    player = None
    results = []
    logger.info("Starting python-vlc station test; duration=%d seconds.", args.duration)
    logger.info("Playback diagnostics and answers are logged to %s.", args.log_file)

    try:
        instance = vlc.Instance("--no-video")
        if instance is None:
            logger.error("Could not initialize libVLC.")
            return 2
        player = instance.media_player_new()

        for name, url in STATIONS:
            logger.info("Station: %s | URL: %s", name, url)
            media = instance.media_new(url)
            try:
                status = play_station(
                    vlc, player, media, name, url, args.duration, logger
                )
            except KeyboardInterrupt:
                logger.info("Test interrupted while playing %s.", name)
                status = "INTERRUPTED"
            except Exception:
                logger.exception("Playback failed unexpectedly for %s.", name)
                status = "PLAY ERROR"
            finally:
                player.stop()
                media.release()

            if status == "INTERRUPTED":
                results.append((name, url, status))
                break

            if status in {"PLAY ERROR", "VLC ERROR", "ENDED EARLY"}:
                logger.warning("Playback status for %s: %s", name, status)
            answer = ask_listener(logger, name)
            if answer == "q":
                results.append((name, url, f"{status}; QUIT BEFORE ANSWER"))
                break

            heard = answer in {"y", "yes"}
            result = f"{status}; {'HEARD' if heard else 'NOT HEARD'}"
            results.append((name, url, result))
            logger.info("RESULT: %s | %s", name, result)

    except KeyboardInterrupt:
        logger.info("Test interrupted.")
    except Exception:
        logger.exception("Could not initialize or operate libVLC.")
        return 2
    finally:
        if player is not None:
            player.stop()
            player.release()
        if instance is not None:
            instance.release()

    logger.info("Station test summary:")
    for name, url, result in results:
        logger.info("SUMMARY: %s | %s | %s", name, result, url)
    logger.info("Full test log: %s", args.log_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
