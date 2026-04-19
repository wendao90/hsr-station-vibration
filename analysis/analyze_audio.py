"""
Analyze audio clips for each event: spectrogram, low/mid/high band energies.
"""
import os, json, wave
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from scipy import signal
import pandas as pd

rcParams['font.sans-serif'] = ['Microsoft YaHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
EVENTS_DIR = os.path.join(BASE, 'events')
OUT_DIR = os.path.join(BASE, 'figures')

with open(os.path.join(EVENTS_DIR, 'events_catalog.json'), 'r', encoding='utf-8') as f:
    catalog = json.load(f)

rows = []

for ev in catalog:
    clip = ev.get('audio_clip')
    if not clip or not os.path.exists(clip):
        continue
    wf = wave.open(clip, 'rb')
    sr = wf.getframerate()
    nframes = wf.getnframes()
    raw = wf.readframes(nframes)
    wf.close()
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    duration = len(samples) / sr

    # Event range within the clip (we padded 1s each side)
    ev_pad_start_in_clip = 1.0
    ev_pad_end_in_clip = duration - 1.0
    ev_mask = np.arange(len(samples)) / sr
    ev_seg = samples[(ev_mask >= ev_pad_start_in_clip) & (ev_mask <= ev_pad_end_in_clip)]
    bg_seg = samples[ev_mask < ev_pad_start_in_clip]  # 1-second baseline
    if len(ev_seg) < 10:
        print(f'{ev["id"]}  [SKIP] event segment too short (clip duration={duration:.1f}s)')
        continue

    # Features
    rms_ev = float(np.sqrt(np.mean(ev_seg**2)))
    rms_bg = float(np.sqrt(np.mean(bg_seg**2))) if len(bg_seg) > 10 else 0.0001
    peak_ev = float(np.max(np.abs(ev_seg)))
    # Frequency bands (Welch)
    f, psd = signal.welch(ev_seg, fs=sr, nperseg=min(1024, len(ev_seg)))
    def bp(a, b):
        m = (f >= a) & (f < b)
        return float(np.trapz(psd[m], f[m])) if np.any(m) else 0
    pwr_low = bp(20, 200)       # rumble
    pwr_mid = bp(200, 2000)     # main acoustic
    pwr_high = bp(2000, 8000)   # hiss/brake squeal
    # Dominant freq in voice band 200-4000
    m = (f >= 50) & (f < 4000)
    dom = float(f[m][np.argmax(psd[m])]) if np.any(m) else 0

    # Audio-to-background ratio
    snr_db = 20 * np.log10(rms_ev / max(rms_bg, 1e-8))

    rows.append({
        'event_id': ev['id'],
        'group': ev['group_desc'],
        'audio_peak': peak_ev,
        'audio_rms': rms_ev,
        'audio_baseline_rms': rms_bg,
        'audio_snr_db': snr_db,
        'audio_dom_hz': dom,
        'audio_pwr_low_20_200': pwr_low,
        'audio_pwr_mid_200_2k': pwr_mid,
        'audio_pwr_high_2k_8k': pwr_high,
    })

    # Plot spectrogram + waveform
    fig, axes = plt.subplots(2, 1, figsize=(11, 5))
    t = np.arange(len(samples)) / sr
    axes[0].plot(t, samples, color='#f0a050', linewidth=0.5)
    axes[0].axvspan(ev_pad_start_in_clip, ev_pad_end_in_clip, color='#60a5fa', alpha=0.15, label='event')
    axes[0].set_xlabel('Time (s) in clip')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title(f'{ev["id"]}  audio  {ev["abs_start"]}~{ev["abs_end"]}  peak={peak_ev:.2f}  SNR={snr_db:.1f}dB')
    axes[0].legend(loc='upper right', fontsize=8)
    axes[0].grid(alpha=0.3)

    f2, tt2, Sxx = signal.spectrogram(samples, fs=sr, nperseg=1024, noverlap=512)
    im = axes[1].pcolormesh(tt2, f2, 10*np.log10(Sxx + 1e-12), cmap='magma', shading='auto')
    axes[1].set_ylim(0, 4000)
    axes[1].set_xlabel('Time (s)')
    axes[1].set_ylabel('Frequency (Hz)')
    axes[1].set_title(f'Audio spectrogram (dominant ≈ {dom:.0f} Hz)')
    axes[1].axvline(ev_pad_start_in_clip, color='#60a5fa', linestyle='--', linewidth=1, alpha=0.8)
    axes[1].axvline(ev_pad_end_in_clip, color='#60a5fa', linestyle='--', linewidth=1, alpha=0.8)

    plt.tight_layout()
    out = os.path.join(OUT_DIR, f'{ev["id"]}_audio.png')
    plt.savefig(out, dpi=110)
    plt.close()
    print(f'{ev["id"]}  audio_rms={rms_ev:.4f}  snr={snr_db:.1f}dB  dom={dom:.0f}Hz  -> {os.path.basename(out)}')

df = pd.DataFrame(rows)
print('\n' + df.to_string())
df.to_csv(os.path.join(BASE, 'audio_summary.csv'), index=False, encoding='utf-8-sig')
print('[OK]', os.path.join(BASE, 'audio_summary.csv'))

# Join with vib summary
vib_df = pd.read_csv(os.path.join(BASE, 'events_summary.csv'))
combined = vib_df.merge(df, on='event_id', how='outer')
combined.to_csv(os.path.join(BASE, 'combined_summary.csv'), index=False, encoding='utf-8-sig')
print('[OK] Combined:', os.path.join(BASE, 'combined_summary.csv'))
print('\n=== Combined summary ===')
print(combined[['event_id','group_desc','peak','rms','snr_db','dominant_freq','audio_rms','audio_snr_db','audio_dom_hz']].to_string())
