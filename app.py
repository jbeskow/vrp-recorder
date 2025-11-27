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
    with open("prompts.txt", "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    return {"prompts": lines}


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
