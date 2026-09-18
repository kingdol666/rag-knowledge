#!/usr/bin/env python3
"""Upload qdcvr-demo.mp4 to YouTube via the YouTube Data API v3.

One-time setup (about 4 minutes, all in your browser):

  1. console.cloud.google.com  ->  create a project (any name)
  2. "APIs & Services" -> "Library" -> enable **YouTube Data API v3**
  3. "APIs & Services" -> "OAuth consent screen"
        User type: External  ->  add yourself as a Test user
  4. "APIs & Services" -> "Credentials" -> "Create credentials"
        -> "OAuth client ID" -> Application type: **Desktop app**
        -> Download JSON  ->  save it next to this file as  client_secret.json
  5. python upload_youtube.py --privacy unlisted

The script opens a browser once for the consent screen; the resulting token is
cached in `token.json` so later runs do not prompt again.

Flags:
  --privacy  unlisted | private | public     (default: unlisted)
  --video    path to the mp4                 (default: ./qdcvr-demo.mp4)
  --thumbnail ./thumbnail.png                (default: auto if the file exists)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET = HERE / "client_secret.json"
TOKEN = HERE / "token.json"

# ── metadata ────────────────────────────────────────────────────────────────
TITLE = ("QDCVR: Content-Verified Retrieval for Knowledge-Base Management "
         "(CIKM Demo)")

DESCRIPTION = """\
QDCVR is a deployable knowledge-base management platform that organizes
documents by what they say, and verifies every retrieval by reading it.

Documents are parsed to structured text and filed into a category base by
reading their content rather than their filename. Long papers are split into
parts that keep their section headers, and tags propagate from a paper to every
part. Retrieval then runs one query-driven protocol: vector-first recall, an
interpretable 0-8 content gate that scores the candidate text actually read, a
librarian fallback over the base shelves, and an explicit not-found contract
when no evidence passes. The platform is exposed to AI agents through 41 MCP
tools.

CHAPTERS
00:00 The problem: nobody can tell whether a retrieved passage answers the query
00:15 Content-based organization - 50 real papers, 5 category bases
00:47 Content-verified retrieval - the NISQ query, live
01:09 The 0-8 content gate and the five-section answer
01:36 The trap: a query for a paper that does not exist
01:54 The honest not-found report
02:19 Agent-native surface and benchmark evidence
02:46 Visit the booth

WHAT IS ON SCREEN
The console footage is a real recording of the running deployment. The NISQ
query returns quantum-physics__1801.00862 (part 1 of 3, 0.62 fused BM25+vector
similarity); the fabricated-paper query returns the BERT paper, which really
does contain the training-epoch strings described in the narration. The two
text cards reproduce, verbatim, a recorded benchmark answer and a recorded
not-found report. Nothing is mocked.

MEASURED (50 real papers, 3.8M characters, 165 indexed documents)
- gold document ranked first in 10/10 questions, 1.6 s mean vector recall
- final content-gate scores 6-8/8, with both librarian rescues succeeding
- three out-of-corpus probes scored 1/8, 1/8 and 0/8 - all returned not-found

Code and run artifacts: https://github.com/kingdol/rag-knowledge
"""

TAGS = [
    "RAG", "retrieval-augmented generation", "knowledge base",
    "content verification", "information retrieval", "MCP",
    "Model Context Protocol", "document management", "CIKM demo",
    "vector search", "BM25", "hallucination",
]


def ensure_deps() -> None:
    need = []
    for mod, pkg in (("googleapiclient", "google-api-python-client"),
                     ("google_auth_oauthlib", "google-auth-oauthlib")):
        try:
            __import__(mod)
        except ImportError:
            need.append(pkg)
    if need:
        print(f"[deps] installing: {' '.join(need)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *need])


def build_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                raise SystemExit(
                    f"missing {CLIENT_SECRET.name}.\n"
                    "Create an OAuth *Desktop app* client in Google Cloud "
                    "(YouTube Data API v3 enabled) and save the downloaded "
                    "JSON here. See the docstring at the top of this file.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        print(f"[auth] token cached -> {TOKEN.name}")
    return build("youtube", "v3", credentials=creds)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(HERE / "qdcvr-demo.mp4"))
    ap.add_argument("--privacy", default="unlisted",
                    choices=["unlisted", "private", "public"])
    ap.add_argument("--thumbnail", default=str(HERE / "thumbnail.png"))
    ap.add_argument("--category", default="28", help="28 = Science & Technology")
    args = ap.parse_args()

    video = Path(args.video)
    if not video.exists():
        raise SystemExit(f"video not found: {video}")

    ensure_deps()

    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = build_service()
    body = {
        "snippet": {
            "title": TITLE,
            "description": DESCRIPTION,
            "tags": TAGS,
            "categoryId": args.category,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": False,
            "license": "youtube",
        },
    }
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024,
                            resumable=True, mimetype="video/mp4")
    print(f"[upload] {video.name} ({video.stat().st_size / 1e6:.1f} MB) "
          f"as {args.privacy} ...")

    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"   {int(status.progress() * 100):3d}%", flush=True)

    vid = resp["id"]
    url = f"https://youtu.be/{vid}"
    print(f"\n[done] {url}")
    print(f"       studio: https://studio.youtube.com/video/{vid}/edit")

    thumb = Path(args.thumbnail)
    if thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid,
                                media_body=MediaFileUpload(str(thumb))).execute()
            print(f"[done] thumbnail set from {thumb.name}")
        except HttpError as e:
            print(f"[warn] thumbnail rejected: {str(e)[:200]}")

    (HERE / "youtube_upload.json").write_text(
        json.dumps({"id": vid, "url": url, "privacy": args.privacy,
                    "title": TITLE}, indent=1), encoding="utf-8")
    print("\nPut this URL into the paper (3 places):")
    print("  paper_demo/tex/sec0_abstract.tex, sec3_demo.tex, sec4_backmatter.tex")
    print("  replacing https://example.org/qdcvr-demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
