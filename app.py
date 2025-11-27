import os
import uuid
import subprocess
import numpy as np
import librosa
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------
# INITIAL SETUP
# ---------------------------------------------------------

app = FastAPI()

# Directories
os.makedirs("recordings", exist_ok=True)
VRP_FILE = "vrp_data.npy"

# Create VRP file if missing
if not os.path.exists(VRP_FILE):
    np.save(VRP_FILE, np.empty((0, 2)))   # columns: [F0_st, Energy_dB]

# Serve static folder
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/prompts")
def get_prompts():
    default_prompts = [
        "Sustain a comfortable vowel",
        "Glide from low to high pitch",
        "Project your voice like on stage",
    ]

    if not os.path.exists("prompts.txt"):
        return {"prompts": default_prompts}

    try:
        with open("prompts.txt", "r") as f:
            lines = [line.strip() for line in f if line.strip()]
        return {"prompts": lines or default_prompts}
    except OSError:
        return {"prompts": default_prompts}


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload audio (WebM/Opus), convert → WAV, extract F0 + SPL,
    update cumulative VRP.
    """

    # Store raw WebM upload
    temp_webm = f"{uuid.uuid4()}.webm"
    temp_webm_path = os.path.join("recordings", temp_webm)

    audio_bytes = await file.read()
    with open(temp_webm_path, "wb") as f:
        f.write(audio_bytes)

    # Output WAV file
    wav_filename = f"{uuid.uuid4()}.wav"
    wav_path = os.path.join("recordings", wav_filename)

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        temp_webm_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        wav_path,
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to convert audio", "details": exc.stderr.decode()},
        )

    # Load audio and extract features
    y, sr = librosa.load(wav_path, sr=16000)

    # Pitch (Hz) using YIN, then convert to semitones
    f0_hz = librosa.yin(y, fmin=50, fmax=800, sr=sr)
    f0_st = librosa.hz_to_midi(f0_hz)  # semitone-like scale

    # Energy (RMS -> dB)
    rms = librosa.feature.rms(y=y)[0]
    energy_db = librosa.amplitude_to_db(rms, ref=1.0)

    # Ensure equal lengths
    min_len = min(len(f0_st), len(energy_db))
    f0_st = f0_st[:min_len]
    energy_db = energy_db[:min_len]

    # Filter out invalid pitch estimates
    valid_mask = np.isfinite(f0_st)
    f0_st = f0_st[valid_mask]
    energy_db = energy_db[valid_mask]

    # Update VRP cumulative data
    vrp_data = np.load(VRP_FILE)
    new_points = np.column_stack((f0_st, energy_db))
    vrp_all = np.vstack((vrp_data, new_points))
    np.save(VRP_FILE, vrp_all)

    return JSONResponse(
        {
            "f0_st": f0_st.tolist(),
            "energy_db": energy_db.tolist(),
            "vrp_all": vrp_all.tolist(),
        }
    )
