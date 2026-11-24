# dev env for web control

```
conda create -n "dev-web-control" python=3.12

conda activate dev-web-control

pip install -r requirements.txt
python3 app.py

```

The **Download / update** tab uses `yt-dlp` to download audio into the
`playtube.home.temp` directory configured in `~/.config/py-radio/config.ini`.
It creates or replaces `~/Music/<playlist-name>.txt` with the playlist URL and
the downloaded audio file paths. Unavailable playlist entries are skipped; if
some tracks are still available, the playlist is saved with those tracks and
the job reports a partial success.

The **Play Local Playlist** tab sends one of the configured local playlist
filenames (`local-IMPREZKA.txt`, `local-10-milions.txt`,
`Eric-Clapton-Live-at-the-Royal-Albert-Hall.txt`, `pyradio_Goralskie.txt`,
`pyradio_Thompson.txt`, or `pyradio_AI.txt`) to the radio player. Each playlist
`.txt` file must be in the radio player's `~/Music` directory. Audio paths in
each file may be absolute or relative to `~/Music`.

The local playlist tab also provides next-track, pause, resume, and volume
controls for the current VLC playback.