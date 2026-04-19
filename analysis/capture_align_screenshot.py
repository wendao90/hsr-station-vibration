"""Capture screenshots of align.html for paper figure, with imported annotations.

Serves a cleaned demo version of notes.txt at request time, and rewrites the
noteRef.noteText inside the alignment JSON to match before import — so the
"关联笔记" column in the status panel shows professional text. Original files
(align.html, notes.txt, alignment_*.json) are left untouched.
"""
import os, json, re, tempfile
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, 'figures')
VIBVIZ = os.path.abspath(os.path.join(BASE, '..', 'vib_viz'))
ALIGN_JSON_SRC = os.path.join(VIBVIZ, 'alignment_2026-04-18-16-29-22.json')
DEMO_NOTES = os.path.join(VIBVIZ, 'notes_demo.txt')
URL = 'http://127.0.0.1:9200/vib_viz/align.html'


def parse_demo_notes(text):
    """Return list of (seconds_since_midnight, line_idx, clean_line)."""
    out = []
    TIME_RE = re.compile(r'(?:(\d{4})-\d+-\d+\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?')
    for idx, raw in enumerate(text.split('\n')):
        m = TIME_RE.search(raw)
        if not m:
            continue
        h, mi = int(m.group(2)), int(m.group(3))
        s = int(m.group(4) or 0)
        sec = h * 3600 + mi * 60 + s
        out.append((sec, idx, raw.strip()))
    return out


def rewrite_note_refs(align_data, demo_entries):
    """For every noteRef in audioMarks, find nearest demo entry and replace noteText."""
    if not demo_entries:
        return
    sorted_entries = sorted(demo_entries, key=lambda t: t[0])
    secs = [e[0] for e in sorted_entries]
    import bisect
    for audio_key, payload in align_data.get('alignData', {}).items():
        for mark in payload.get('audioMarks', []):
            nr = mark.get('noteRef')
            if not nr:
                continue
            target = nr.get('noteSec', 0)
            i = bisect.bisect_left(secs, target)
            candidates = []
            if i > 0:
                candidates.append(sorted_entries[i - 1])
            if i < len(sorted_entries):
                candidates.append(sorted_entries[i])
            best = min(candidates, key=lambda t: abs(t[0] - target))
            nr['noteText'] = best[2]
            nr['lineIdx'] = best[1]
            nr['noteSec'] = best[0]

with sync_playwright() as p:
    # --- Build a demo-sanitized alignment JSON in a temp file ---
    with open(DEMO_NOTES, encoding='utf-8') as f:
        demo_notes_body = f.read()
    demo_entries = parse_demo_notes(demo_notes_body)
    with open(ALIGN_JSON_SRC, encoding='utf-8') as f:
        align_obj = json.load(f)
    rewrite_note_refs(align_obj, demo_entries)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.json', prefix='alignment_demo_')
    with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
        json.dump(align_obj, f, ensure_ascii=False)

    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1600, 'height': 1000}, device_scale_factor=2)
    page = context.new_page()
    # Auto-confirm any window.confirm() dialogs
    page.on('dialog', lambda d: d.accept())
    # Intercept notes.txt request and serve the cleaned demo version instead
    def _route_notes(route):
        if route.request.url.endswith('/notes.txt'):
            route.fulfill(status=200, content_type='text/plain; charset=utf-8', body=demo_notes_body)
        else:
            route.continue_()
    page.route('**/notes.txt', _route_notes)
    page.goto(URL)
    page.wait_for_timeout(3500)

    # Import the demo-sanitized alignment JSON
    page.set_input_files('#importFile', tmp_path)
    page.wait_for_timeout(2500)

    # Screenshot
    out1 = os.path.join(OUT_DIR, 'align_tool_overview.png')
    page.screenshot(path=out1, full_page=False)
    print(f'[OK] {out1}')

    browser.close()
    try:
        os.remove(tmp_path)
    except OSError:
        pass
