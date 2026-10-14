import os, uuid, shutil, yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"], expose_headers=["Content-Disposition"])

class Info(BaseModel):
    url: str

class Dl(BaseModel):
    url: str
    kind: str = "video"      # video | audio
    height: int = 720
    audio_fmt: str = "mp3"   # mp3 | m4a
    abr: int = 192

@app.get("/")
def home():
    return {"status": "SnapDown API is running"}

@app.post("/api/info")
def info(r: Info):
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as y:
            i = y.extract_info(r.url, download=False)
    except Exception as e:
        raise HTTPException(400, str(e)[:300])
    hs = sorted({f["height"] for f in i.get("formats", [])
                 if f.get("height") and f.get("vcodec") != "none"})
    return {"title": i.get("title"), "thumbnail": i.get("thumbnail"),
            "duration": i.get("duration"), "heights": hs}

@app.post("/api/download")
def download(r: Dl):
    d = os.path.join("downloads", uuid.uuid4().hex)
    os.makedirs(d, exist_ok=True)
    o = {"outtmpl": f"{d}/%(title).80s.%(ext)s", "noplaylist": True, "quiet": True}
    if r.kind == "audio":
        o["format"] = "bestaudio/best"
        o["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                "preferredcodec": r.audio_fmt,
                                "preferredquality": str(r.abr)}]
    else:
        o["format"] = f"bestvideo[height<={r.height}]+bestaudio/best[height<={r.height}]/best"
        o["merge_output_format"] = "mp4"
    try:
        with yt_dlp.YoutubeDL(o) as y:
            y.extract_info(r.url, download=True)
        path = os.path.join(d, os.listdir(d)[0])
    except Exception as e:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(400, str(e)[:300])
    return FileResponse(path, filename=os.path.basename(path),
                        background=BackgroundTask(shutil.rmtree, d, True))
