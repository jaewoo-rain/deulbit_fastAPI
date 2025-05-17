from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List
import httpx
import datetime
import os

app = FastAPI()

# 베이스 저장 디렉터리
OUTPUT_DIR = "audio_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class TTSRequest(BaseModel):
    script: str
    voice: str
    vibeKey: str
    vibePrompt: str
    fileName: str   # 이 이름으로 하위 폴더를 만들고, 파일명에도 사용

@app.post("/generate-audio")
async def generate_audio(requests: List[TTSRequest]):
    """
    요청 형식 (application/json):
    [
      {
        "script": "...",
        "voice": "alloy",
        "vibeKey": "Calm",
        "vibePrompt": "...",
        "fileName": "batch1"
      },
      {
        "script": "...",
        "voice": "volle",
        "vibeKey": "Exten",
        "vibePrompt": "...",
        "fileName": "batch1"
      }
    ]
    반환 형식: [
      {"path": "audio_outputs/batch1", "filename": "batch10.wav"},
      {"path": "audio_outputs/batch1", "filename": "batch11.wav"}
    ]
    """
    results = []

    async with httpx.AsyncClient() as client:
        for idx, req in enumerate(requests):
            # 1) 디렉터리 생성 (OUTPUT_DIR/<fileName>)
            out_dir = os.path.join(OUTPUT_DIR, req.fileName)
            os.makedirs(out_dir, exist_ok=True)

            # 2) OpenAI.fm 호출 준비
            url = "https://www.openai.fm/api/generate"
            boundary = "----WebKitFormBoundarya027BOtfh6crFn7A"
            body_lines = []
            for name, value in [
                ("input", req.script),
                ("voice", req.voice.lower()),
                ("vibe", req.vibeKey),
                ("prompt", req.vibePrompt)
            ]:
                body_lines.append(f"--{boundary}")
                body_lines.append(f'Content-Disposition: form-data; name="{name}"\r\n')
                body_lines.append(value)
            body_lines.append(f"--{boundary}--")
            body = "\r\n".join(body_lines).encode("utf-8")

            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Origin": "https://www.openai.fm",
                "User-Agent": "fastapi-tts-client"
            }

            # 3) 요청 및 응답 처리
            resp = await client.post(url, headers=headers, content=body)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            if "audio" not in resp.headers.get("Content-Type", ""):
                raise HTTPException(status_code=500, detail="Invalid response content type")

            # 4) 파일명: fileName + index.wav
            filename = f"{req.fileName}{idx}.wav"
            file_path = os.path.join(out_dir, filename)
            with open(file_path, "wb") as f:
                f.write(resp.content)

            results.append({
                "path": out_dir,
                "filename": filename
            })

    return JSONResponse(results)


# 오디오 다운로드 엔드포인트
class DownloadRequest(BaseModel):
    # 클라이언트가 POST 바디로 보낼 두 가지 정보
    path: str      # 예: "audio_outputs" 또는 "/home/app/audio_outputs"
    filename: str  # 예: "output_test_20250517_235959.wav"

@app.post("/download-audio")
async def download_audio(req: DownloadRequest):
    # 요청받은 디렉터리와 파일명을 합쳐 절대 경로 생성
    file_path = os.path.abspath(os.path.join(req.path, req.filename))

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")

    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        filename=req.filename
    )


# =========================
# 실행 및 테스트 가이드
# =========================
# 1) uvicorn 서버 실행:
#    uvicorn main:app --reload --host 0.0.0.0 --port 8000
#    - main.py 파일명에 따라 모듈 경로를 조정하세요.

# 2) 오디오 생성 POST 요청 예시 (curl):
#    curl -X POST http://localhost:8000/generate-audio \
#      -H "Content-Type: application/json" \
#      -d '{
#            "script": "안녕하세요, 테스트 중입니다.",
#            "voice": "alloy",
#            "vibeKey": "Calm",
#            "vibePrompt": "Voice Affect: Calm, composed; speaks with a soothing tone..."
#          }'
#    응답 JSON에 저장된 파일명과 경로가 표시됩니다.

# 3) 오디오 다운로드 GET 요청 예시:
#    curl http://localhost:8000/download/{filename} --output downloaded.wav
#    - {filename}은 POST 응답에서 받은 파일명으로 교체하세요.

# 4) audio_outputs/ 폴더 내부에서 바로 재생하거나 이동해서 사용 가능합니다.
