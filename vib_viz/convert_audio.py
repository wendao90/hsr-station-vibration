"""Convert all m4a files to WAV (mono, 16kHz) for consistent browser playback."""
import os, subprocess
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
SOUND_DIR = os.path.join(PROJECT_DIR, "sound")
OUT_DIR = os.path.join(BASE_DIR, "audio_wav")

os.makedirs(OUT_DIR, exist_ok=True)

for f in sorted(os.listdir(SOUND_DIR)):
    if not f.endswith('.m4a'): continue
    in_path = os.path.join(SOUND_DIR, f)
    out_name = f.replace('.m4a', '.wav')
    out_path = os.path.join(OUT_DIR, out_name)
    if os.path.exists(out_path):
        print(f'Skip (exists): {out_name}')
        continue
    cmd = [FFMPEG, '-y', '-i', in_path, '-ac', '1', '-ar', '16000', '-acodec', 'pcm_s16le', out_path]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f'FAIL: {f}: {r.stderr[-200:]}')
        continue
    sz_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f'OK: {out_name} ({sz_mb:.1f} MB)')

print('\nDone. Total size:', sum(os.path.getsize(os.path.join(OUT_DIR, f))
      for f in os.listdir(OUT_DIR) if f.endswith('.wav')) / 1024 / 1024, 'MB')
