"""
Prepare the public release bundle under D:/projects/vib/data_release/.

Strategy
--------
• Vibration:    copy the 9 xls files actually used in the paper (service desk
                M1 + floor M2 + platform M3 range).
• Audio:        cut short WAV clips corresponding to each annotated train-pass
                event (±3 s padding) and to each clean-background segment.
                This removes the long continuous recordings — which contain
                station announcements, bystander speech and personal side
                remarks — while preserving everything referenced by the paper's
                quantitative analysis.
• Annotations:  copy the alignment JSON (note texts already scrubbed via
                notes_demo.txt mapping) + the cleaned demo notes as notes.txt.
• Derived:      copy the npz event/baseline segments + summary CSVs.
• Docs:         README.md / LICENSE / DATA-LICENSE / CITATION.cff.

Run:
    python scripts/prepare_release.py
"""
import os, sys, io, json, re, shutil, subprocess
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data_release'
SOUND = ROOT / 'sound'
VIB_DATA = ROOT / 'vib_data'
VIB_VIZ = ROOT / 'vib_viz'
ANALYSIS = ROOT / 'analysis'

# --- xls files used in the paper (service desk + floor + platform) ---
# M1 service desk: g(1)..g(9); M2 floor: g(11)..g(14); M3 platform: g(15)/g(16)
USED_XLS = [f'g ({i}).xls' for i in range(1, 17) if i != 10]

# --- Audio clipping padding around annotated intervals ---
PAD_SECONDS = 3.0


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def copy_xls():
    target = OUT / 'vibration'
    ensure_dir(target)
    count = 0
    for name in USED_XLS:
        src = VIB_DATA / name
        if not src.exists():
            print(f'[skip] {name} missing')
            continue
        shutil.copy2(src, target / name)
        count += 1
    print(f'[ok] vibration: {count} xls files')


def load_alignment():
    """Load the canonical alignment JSON and scrub note texts via demo notes."""
    align_src = VIB_VIZ / 'alignment_2026-04-18-16-29-22.json'
    demo_src = VIB_VIZ / 'notes_demo.txt'
    with open(align_src, encoding='utf-8') as f:
        align = json.load(f)
    with open(demo_src, encoding='utf-8') as f:
        demo_notes = f.read()

    # Build (sec_of_day, text) map from demo notes
    import bisect
    demo_map = []
    TIME_RE = re.compile(r'(\d{1,2}):(\d{2})(?::(\d{2}))?')
    for idx, raw in enumerate(demo_notes.split('\n')):
        m = TIME_RE.search(raw)
        if not m:
            continue
        sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)
        demo_map.append((sec, idx, raw.strip()))
    demo_map.sort()
    secs = [e[0] for e in demo_map]

    for audio_key, payload in align.get('alignData', {}).items():
        for mark in payload.get('audioMarks', []):
            nr = mark.get('noteRef')
            if not nr:
                continue
            target = nr.get('noteSec', 0)
            i = bisect.bisect_left(secs, target)
            cands = []
            if i > 0:
                cands.append(demo_map[i - 1])
            if i < len(demo_map):
                cands.append(demo_map[i])
            best = min(cands, key=lambda t: abs(t[0] - target))
            nr['noteText'] = best[2]
            nr['lineIdx'] = best[1]
            nr['noteSec'] = best[0]
    return align, demo_notes


def write_annotations(align, demo_notes):
    target = OUT / 'annotations'
    ensure_dir(target)
    with open(target / 'alignment.json', 'w', encoding='utf-8') as f:
        json.dump(align, f, ensure_ascii=False, indent=2)
    with open(target / 'notes.txt', 'w', encoding='utf-8') as f:
        f.write(demo_notes)
    print(f'[ok] annotations: alignment.json + notes.txt')


def find_audio_for(name):
    """Map alignment-JSON audio key (with 点/分) to the actual sound/*.m4a file."""
    # Keys look like "2026年04月06日 19点59分.m4a"; file names match exactly
    p = SOUND / name
    if p.exists():
        return p
    # Fuzzy: strip any full-width spaces
    for cand in SOUND.iterdir():
        if cand.name.replace(' ', '') == name.replace(' ', ''):
            return cand
    return None


def extract_audio_clips(align):
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    target = OUT / 'audio_clips'
    ensure_dir(target)

    # Walk all events in alignment JSON (train_pass + clean_bgnd intervals)
    n_clips = 0
    for audio_key, payload in align.get('alignData', {}).items():
        src = find_audio_for(audio_key)
        if src is None:
            print(f'[skip audio] missing: {audio_key}')
            continue
        events = payload.get('events', [])
        if not events:
            continue
        for ev in events:
            ev_type = ev.get('type', 'event')
            t0 = max(0.0, ev.get('audioStart', 0) - PAD_SECONDS)
            t1 = ev.get('audioEnd', t0) + PAD_SECONDS
            dur = max(0.0, t1 - t0)
            if dur < 1.0:
                continue
            # Pad time reference: audio key minutes should be subtracted, but we store
            # clip seconds relative to the parent m4a (same as alignment JSON)
            out_name = f'{src.stem}__{ev_type}__{t0:07.1f}-{t1:07.1f}.wav'
            out_name = out_name.replace(' ', '_')
            out_path = target / out_name
            if out_path.exists():
                n_clips += 1
                continue
            cmd = [FFMPEG, '-y', '-hide_banner', '-loglevel', 'error',
                   '-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', str(src),
                   '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(out_path)]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode != 0:
                print(f'[err] {out_name}: {r.stderr[-180:].decode(errors="replace")}')
                continue
            n_clips += 1
    print(f'[ok] audio_clips: {n_clips} wav files')


def copy_derived():
    target = OUT / 'derived'
    ensure_dir(target)
    # Summary CSVs
    for csv_name in ['clean_segments_summary.csv', 'scene_summary.csv',
                     'iso2631_and_octave.csv']:
        src = ANALYSIS / csv_name
        if src.exists():
            shutil.copy2(src, target / csv_name)
    # Event / baseline npz
    npz_target = target / 'segments'
    ensure_dir(npz_target)
    events_dir = ANALYSIS / 'events'
    count = 0
    if events_dir.exists():
        for f in events_dir.iterdir():
            if f.suffix == '.npz' and 'subway' not in f.name:
                shutil.copy2(f, npz_target / f.name)
                count += 1
    print(f'[ok] derived: {count} npz + summary CSVs')


def copy_docs():
    for name in ['README.md', 'LICENSE', 'DATA-LICENSE', 'CITATION.cff']:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, OUT / name)
    print('[ok] docs copied')


def main():
    ensure_dir(OUT)
    print(f'Building release under: {OUT}\n')
    copy_xls()
    align, demo_notes = load_alignment()
    write_annotations(align, demo_notes)
    extract_audio_clips(align)
    copy_derived()
    copy_docs()
    # Summary
    total_mb = sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()) / 1024 / 1024
    print(f'\nRelease bundle built. Total size: {total_mb:.1f} MB')


if __name__ == '__main__':
    main()
