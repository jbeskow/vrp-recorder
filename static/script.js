let mediaRecorder;
let audioChunks = [];
let lastBlob = null;
let prompts = [];
let promptIdx = 0;

async function loadPrompts() {
    const r = await fetch("/prompts");
    const data = await r.json();
    prompts = data.prompts;
    document.getElementById("prompt").innerText = prompts[promptIdx];
}
loadPrompts();

// --- Recording ---
document.getElementById("recordBtn").onclick = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    audioChunks = [];
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = onStopRecording;

    mediaRecorder.start();
    document.getElementById("recordBtn").disabled = true;
    document.getElementById("stopBtn").disabled = false;
};

document.getElementById("stopBtn").onclick = () => {
    mediaRecorder.stop();
    document.getElementById("recordBtn").disabled = false;
    document.getElementById("stopBtn").disabled = true;
};

async function onStopRecording() {
    lastBlob = new Blob(audioChunks, { type: "audio/wav" });
    upload(lastBlob);
}

// --- Playback ---
document.getElementById("playBtn").onclick = () => {
    if (!lastBlob) return;
    const audio = new Audio(URL.createObjectURL(lastBlob));
    audio.play();
};

// --- Upload to server ---

async function upload(blob) {
    const form = new FormData();
    form.append("file", blob, "recording.webm");

    const resp = await fetch("/upload", {
        method: "POST",
        body: form
    });

    const data = await resp.json();

    console.log("SERVER DATA:", data);

    // >>> NEW VRP CALL <<<
    drawVRP(data.f0_st, data.energy_db, data.vrp_all);

    document.getElementById("playBtn").disabled = false;
}

// --- Histogram Plotting ---
function drawHistogram(divId, hist, label) {
    const counts = hist[0];
    const bin_edges = hist[1];

    const trace = {
        x: bin_edges,
        y: [...counts, counts[counts.length-1]],
        type: 'bar'
    };

    Plotly.newPlot(divId, [trace], { title: label });
}

function drawVRP(f0_last, energy_last, vrp_all) {
    let x = vrp_all.map(p => p[0]);
    let y = vrp_all.map(p => p[1]);

    let heat = {
        x: x,
        y: y,
        type: 'histogram2d',
        colorscale: 'Blues',
        nbinsx: 60,
        nbinsy: 60,
        showscale: true,
        name: "Cumulative VRP"
    };

    let last_scatter = {
        x: f0_last,
        y: energy_last,
        mode: 'markers',
        marker: { color: 'red', size: 6 },
        name: 'Last recording'
    };

    Plotly.newPlot('vrp_plot', [heat, last_scatter], {
        title: 'Voice Range Profile',
        xaxis: { title: 'F0 (semitones)' },
        yaxis: { title: 'SPL (dB)' }
    });
}