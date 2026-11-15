"""Extraction gratuite d'un reel : légende, transcription locale (Whisper) et images clés.

    python -m popote.reel https://www.instagram.com/reel/XXXX/ [--cookies cookies.txt]

Sortie : JSON {source, auteur, duree, legende, transcription, images[]} ; images dans out/reel/.
- yt-dlp télécharge la vidéo (TikTok, YouTube Shorts : en général sans connexion).
- Instagram refuse souvent les serveurs sans connexion : passer --cookies (compte secondaire
  conseillé) ou se rabattre sur une capture de la légende. Ne jamais publier ce fichier de cookies.
- faster-whisper transcrit sur le processeur, sans coût (modèle « small », ~1 min pour un reel).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "out" / "reel"


def extract(url: str, cookies: str | None = None, frames: int = 6, whisper_model: str = "small") -> dict:
    import yt_dlp

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("frame_*.jpg"):
        old.unlink()
    tmp = Path(tempfile.mkdtemp())
    opts = {"outtmpl": str(tmp / "video.%(ext)s"), "format": "mp4/best[height<=720]/best",
            "quiet": True, "noprogress": True}
    if cookies:
        opts["cookiefile"] = cookies
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        video = next(tmp.glob("video.*"), None)
        result = {"source": url, "auteur": info.get("uploader") or info.get("channel"),
                  "duree": info.get("duration"), "legende": (info.get("description") or "").strip(),
                  "transcription": None, "images": []}
        if video and shutil.which("ffmpeg"):
            dur = float(info.get("duration") or 30)
            for i in range(frames):
                out = OUT / f"frame_{i:02d}.jpg"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{dur * (i + .5) / frames:.2f}",
                                "-i", str(video), "-frames:v", "1", "-vf", "scale=720:-2", str(out)], check=False)
                if out.exists():
                    result["images"].append(str(out))
        if video:
            try:
                from faster_whisper import WhisperModel
                model = WhisperModel(whisper_model, device="cpu", compute_type="int8")
                segs, _ = model.transcribe(str(video), vad_filter=True)
                result["transcription"] = " ".join(s.text.strip() for s in segs) or None
            except ImportError:
                result["transcription"] = None
        return result
    except Exception as e:  # yt-dlp lève des erreurs variées : connexion requise, contenu privé…
        return {"source": url, "erreur": str(e)[:300],
                "suite": "Demander une capture de la légende dépliée, ou réessayer avec --cookies."}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(prog="popote.reel")
    ap.add_argument("url")
    ap.add_argument("--cookies")
    ap.add_argument("--frames", type=int, default=6)
    a = ap.parse_args()
    print(json.dumps(extract(a.url, a.cookies, a.frames), ensure_ascii=False, indent=1))
    sys.exit(0)


if __name__ == "__main__":
    main()
