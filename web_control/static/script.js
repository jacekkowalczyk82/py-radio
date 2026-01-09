document.addEventListener('DOMContentLoaded', () => {
    const volumeSlider = document.getElementById('volume-slider');
    const volumeValue = document.getElementById('volume-value');
    const stopBtn = document.getElementById('btn-stop');
    const statusIndicator = document.getElementById('status-indicator');
    const stationCards = document.querySelectorAll('.station-card');

    let currentVolume = 100;

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

            sendCommand('play', name, url, currentVolume);
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
