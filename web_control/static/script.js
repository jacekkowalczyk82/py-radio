document.addEventListener('DOMContentLoaded', () => {
    const volumeSlider = document.getElementById('volume-slider');
    const volumeValue = document.getElementById('volume-value');
    const stopBtn = document.getElementById('btn-stop');
    const statusIndicator = document.getElementById('status-indicator');
    const stationCards = document.querySelectorAll('.station-card');
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const playlistForm = document.getElementById('playlist-form');
    const playlistJobStatus = document.getElementById('playlist-job-status');
    const localVolumeSlider = document.getElementById('local-volume-slider');
    const localVolumeValue = document.getElementById('local-volume-value');
    const nextBtn = document.getElementById('btn-next');
    const pauseBtn = document.getElementById('btn-pause');
    const resumeBtn = document.getElementById('btn-resume');
    let activePlaylistJob = null;

    let currentVolume = 100;

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(tab => tab.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            button.classList.add('active');
            document.getElementById(button.dataset.tab).classList.add('active');
        });
    });

    playlistForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const submitButton = playlistForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        playlistJobStatus.textContent = 'Starting playlist update...';
        playlistJobStatus.className = 'playlist-job-status';

        try {
            const response = await fetch('/api/playlists', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: playlistForm.elements.url.value.trim(),
                    name: playlistForm.elements.name.value.trim()
                })
            });
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.message || 'Could not start playlist update.');
            }

            activePlaylistJob = result.job_id;
            await monitorPlaylistJob(submitButton);
        } catch (error) {
            playlistJobStatus.textContent = error.message;
            playlistJobStatus.classList.add('error');
            activePlaylistJob = null;
            submitButton.disabled = false;
        }
    });

    async function monitorPlaylistJob(submitButton) {
        while (activePlaylistJob) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            const response = await fetch(`/api/playlists/${activePlaylistJob}`);
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.message || 'Could not check playlist update status.');
            }

            playlistJobStatus.textContent = result.message;
            if (result.status !== 'running') {
                if (result.status === 'error') {
                    playlistJobStatus.classList.add('error');
                } else {
                    playlistJobStatus.classList.add('success');
                }
                activePlaylistJob = null;
                submitButton.disabled = false;
            }
        }
    }

    // Volume Slider Logic
    volumeSlider.addEventListener('input', (e) => {
        currentVolume = e.target.value;
        volumeValue.textContent = `${currentVolume}%`;
    });

    volumeSlider.addEventListener('change', () => {
        // Send volume update when slider is released (optional, or just send with play)
        // ideally we might want a separate Volume Only action, but for now 
        // we'll update local state and send with next play, OR trigger a re-play of current station if we knew it?
        // Simpler: Just rely on next play, OR send a special 'volume' action if backend supported it.
        // The current requirements specify: "wybrac stacje, volume level i ewentualnie stop".
        // It implies setting volume is part of choosing station OR independent?
        // Our backend sends volume with every command.
    });

    localVolumeSlider.addEventListener('input', () => {
        localVolumeValue.textContent = `${localVolumeSlider.value}%`;
    });

    localVolumeSlider.addEventListener('change', () => {
        sendCommand('volume', null, null, localVolumeSlider.value);
    });

    nextBtn.addEventListener('click', () => {
        sendCommand('next', null, null, localVolumeSlider.value);
    });

    pauseBtn.addEventListener('click', () => {
        sendCommand('pause', null, null, localVolumeSlider.value);
    });

    resumeBtn.addEventListener('click', () => {
        sendCommand('resume', null, null, localVolumeSlider.value);
    });

    // Stop Button
    stopBtn.addEventListener('click', () => {
        sendCommand('stop', null, null, 0);
        updateUIState(null);
    });

    // Station Selection
    stationCards.forEach(card => {
        card.addEventListener('click', () => {
            const name = card.dataset.name;
            const url = card.dataset.url;

            const action = card.classList.contains('local-playlist-card')
                ? 'play_local_playlist'
                : card.classList.contains('playlist-card') ? 'play_playlist' : 'play';
            sendCommand(action, name, url, currentVolume);
            updateUIState(card);
        });
    });

    async function sendCommand(action, name, url, volume) {
        statusIndicator.textContent = "Sending...";
        statusIndicator.className = "status-indicator";

        try {
            const response = await fetch('/api/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: action,
                    name: name,
                    station: url,
                    volume: parseInt(volume)
                })
            });

            const data = await response.json();

            if (response.ok) {
                statusIndicator.textContent = "Command Sent ✓";
                statusIndicator.classList.add('active');
                setTimeout(() => {
                    statusIndicator.classList.remove('active');
                    statusIndicator.textContent = "Ready";
                }, 2000);
            } else {
                statusIndicator.textContent = "Error!";
                console.error('Error:', data.message);
            }
        } catch (error) {
            console.error('Network Error:', error);
            statusIndicator.textContent = "Network Error";
        }
    }

    function updateUIState(activeCard) {
        stationCards.forEach(c => c.classList.remove('playing'));
        if (activeCard) {
            activeCard.classList.add('playing');
        }
    }
});
