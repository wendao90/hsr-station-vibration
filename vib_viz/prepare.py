"""
Preprocessing script: converts raw xls + m4a into web-ready files.
Usage: python prepare.py [--dataset ID] [--all]
"""
import json, os, sys, subprocess, wave, struct
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
VIB_DIR = os.path.join(PROJECT_DIR, "vib_data")
SOUND_DIR = os.path.join(PROJECT_DIR, "sound")
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
DATASETS_JSON = os.path.join(BASE_DIR, "datasets.json")

# Find ffmpeg from imageio_ffmpeg
try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"


def load_config():
    with open(DATASETS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def time_str_to_seconds(ts):
    """Parse ISO time string to total seconds since midnight."""
    from datetime import datetime
    dt = datetime.fromisoformat(ts)
    return dt.hour * 3600 + dt.minute * 60 + dt.second


def process_vibration(ds, out_dir):
    """Convert xls to downsampled data.json."""
    vib_path = os.path.join(VIB_DIR, ds["vibFile"])
    if not os.path.exists(vib_path):
        print(f"  [SKIP] Vibration file not found: {ds['vibFile']}")
        return None

    df = pd.read_excel(vib_path)
    step = max(1, len(df) // 4000)  # ~4000 points max
    ds_df = df.iloc[::step].reset_index(drop=True)

    data = {
        "time": np.round(ds_df["Time (s)"].values, 3).tolist(),
        "ax": np.round(ds_df["Linear Acceleration x (m/s^2)"].values, 5).tolist(),
        "ay": np.round(ds_df["Linear Acceleration y (m/s^2)"].values, 5).tolist(),
        "az": np.round(ds_df["Linear Acceleration z (m/s^2)"].values, 5).tolist(),
        "abs_acc": np.round(ds_df["Absolute acceleration (m/s^2)"].values, 5).tolist(),
    }

    out_path = os.path.join(out_dir, "data.json")
    with open(out_path, "w") as f:
        json.dump(data, f)

    duration = df["Time (s)"].max()
    print(f"  Vibration: {len(df)} rows -> {len(ds_df)} points, {duration:.1f}s")
    return duration


def process_audio(ds, out_dir, vib_duration):
    """Extract audio segment aligned to vibration data, produce WAV + peaks JSON."""
    audio_path = os.path.join(SOUND_DIR, ds["audioFile"])
    if not os.path.exists(audio_path):
        print(f"  [SKIP] Audio file not found: {ds['audioFile']}")
        return

    vib_start = time_str_to_seconds(ds["vibStartTime"])
    audio_start = time_str_to_seconds(ds["audioStartTime"])
    offset = vib_start - audio_start  # seconds into audio where vib data starts

    if vib_duration is None:
        vib_duration = 200

    wav_path = os.path.join(out_dir, "audio_segment.wav")

    # Extract with ffmpeg
    cmd = [
        FFMPEG, "-y",
        "-ss", str(max(0, offset)),
        "-t", str(vib_duration + 2),  # small margin
        "-i", audio_path,
        "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
        wav_path
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"  [ERROR] ffmpeg failed: {result.stderr[-200:]}")
        return

    # Generate waveform peaks
    try:
        wf = wave.open(wav_path, "rb")
        sr = wf.getframerate()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)
        wf.close()

        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        num_bins = 2000
        samples_per_bin = max(1, len(samples) // num_bins)
        actual_bins = len(samples) // samples_per_bin

        pos, neg = [], []
        for i in range(actual_bins):
            chunk = samples[i * samples_per_bin:(i + 1) * samples_per_bin]
            pos.append(float(np.max(chunk)))
            neg.append(float(np.min(chunk)))

        peaks = {
            "pos": [round(v, 4) for v in pos],
            "neg": [round(v, 4) for v in neg],
            "duration": nframes / sr,
            "sampleRate": sr,
            "numBins": actual_bins
        }

        peaks_path = os.path.join(out_dir, "waveform_peaks.json")
        with open(peaks_path, "w") as f:
            json.dump(peaks, f)

        sz_mb = os.path.getsize(wav_path) / 1024 / 1024
        print(f"  Audio: offset={offset:.0f}s, wav={sz_mb:.1f}MB, {actual_bins} peak bins")
    except Exception as e:
        print(f"  [ERROR] Waveform peaks: {e}")


def process_dataset(ds):
    ds_id = ds["id"]
    out_dir = os.path.join(DATASETS_DIR, ds_id)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n[{ds_id}] {ds['name']}")
    vib_dur = process_vibration(ds, out_dir)
    process_audio(ds, out_dir, vib_dur)

    # Create empty annotations if not exists
    ann_path = os.path.join(out_dir, "annotations.json")
    if not os.path.exists(ann_path):
        with open(ann_path, "w") as f:
            json.dump({"datasetId": ds_id, "annotations": []}, f, indent=2)


def main():
    config = load_config()
    datasets = config["datasets"]

    if len(sys.argv) > 1 and sys.argv[1] == "--dataset":
        target = sys.argv[2]
        datasets = [d for d in datasets if d["id"] == target]
        if not datasets:
            print(f"Dataset '{target}' not found")
            sys.exit(1)

    print(f"Processing {len(datasets)} dataset(s)...")
    for ds in datasets:
        process_dataset(ds)
    print("\nDone!")


if __name__ == "__main__":
    main()
