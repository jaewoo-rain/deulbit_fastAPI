from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import httpx
import datetime
import os

# FastAPI 앱 생성
app = FastAPI()

# 저장 디렉토리
OUTPUT_DIR = "audio_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 요청 바디 모델 정의
class TTSRequest(BaseModel):
    script: str
    voice: str
    vibeKey: str
    vibePrompt: str

# 오디오 생성 엔드포인트
@app.post("/generate-audio")
async def generate_audio(request: TTSRequest):
    """
    요청 형식 (application/json):
      {
        "script": "안녕하세요",
        "voice": "alloy",
        "vibeKey": "Calm",
        "vibePrompt": "Voice Affect: Calm, composed; speaks with a soothing tone..."
      }
    반환 형식: JSON { filename, path }
    """
    url = "https://www.openai.fm/api/generate"
    boundary = "----WebKitFormBoundarya027BOtfh6crFn7A"

    # multipart/form-data 바디 구성
    body_lines = []
    for name, value in [
        ("input", request.script),
        ("voice", request.voice.lower()),
        ("vibe", request.vibeKey),
        ("prompt", request.vibePrompt)
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

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, content=body)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        content_type = resp.headers.get("Content-Type", "")
        if "audio" not in content_type:
            raise HTTPException(status_code=500, detail="Invalid response content type")

        # 파일 저장
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{timestamp}.wav"
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "wb") as f:
            f.write(resp.content)

    return JSONResponse({"filename": filename, "path": path})

# 오디오 다운로드 엔드포인트
@app.get("/download/{filename}")
async def download_audio(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/wav", filename=filename)

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
