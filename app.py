from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

class URLRequest(BaseModel):
    url: str

@app.post("/download")
def download_instagram(request: URLRequest):
    url = request.url
    try:
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'skip_download': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info['url']
        return {"video_url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
