from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import os
import uuid

app = FastAPI(title="SnapDown Pro Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class InfoRequest(BaseModel):
    url: str

class DownloadRequest(BaseModel):
    url: str
    format_id: str

@app.get("/")
def home():
    return {"status": "SnapDown API is running"}

@app.post("/api/info")
def get_video_info(req: InfoRequest):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            formats = []
            for f in info.get('formats', []):
                if f.get('ext') in ['mp4', 'm4a', 'mp3']:
                    formats.append({
                        'format_id': f.get('format_id'),
                        'resolution': f.get('resolution') or f.get('format_note') or 'Audio',
                        'ext': f.get('ext'),
                        'filesize': f.get('filesize') or f.get('filesize_approx') or 0
                    })
            return {
                "title": info.get('title', 'Video'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "formats": formats[-8:]
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/download")
def download_video(req: DownloadRequest, background_tasks: BackgroundTasks):
    file_id = str(uuid.uuid4())[:8]
    output_template = f"{DOWNLOAD_DIR}/{file_id}_%(title)s.%(ext)s"
    
    ydl_opts = {
        'format': req.format_id if req.format_id else 'best',
        'outtmpl': output_template,
        'quiet': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=True)
            filename = ydl.prepare_filename(info)
            
            def cleanup():
                if os.path.exists(filename):
                    os.remove(filename)

            background_tasks.add_task(cleanup)
            
            return FileResponse(
                path=filename, 
                filename=os.path.basename(filename),
                media_type='application/octet-stream'
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
