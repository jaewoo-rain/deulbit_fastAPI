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

# 환경 변수에서 OpenAI API 키 읽기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Please set the OPENAI_API_KEY environment variable.")

# 요청 바디 모델 정의 (vibeKey, vibePrompt는 공식 TTS에서 지원되지 않으므로 무시됨)
class TTSRequest(BaseModel):
    script: str
    voice: str
    vibeKey: str = None
    vibePrompt: str = None

# 공식 OpenAI 유료 TTS 생성 엔드포인트
@app.post("/generate-audio")
async def generate_audio(request: TTSRequest):
    """
    요청 형식 (application/json):
      {
        "script": "안녕하세요",
        "voice": "alloy",            # 지원되는 voice preset
        "vibeKey": "Calm",          # 내부 사용되지 않음
        "vibePrompt": "..."         # 내부 사용되지 않음
      }
    반환 형식: JSON { filename, path }
    """
    # OpenAI 유료 TTS URL 및 헤더
    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    # 요청 페이로드 (vibe는 공식 API가 지원하지 않아 script만 전달)
    # 1) LLM에게 SSML 생성 요청
    ssml_template = f"""
        <speak>
        <!-- 1) 울먹거림: 느리고 낮은 톤, 중간중간 끊김 -->
        <prosody rate="slow" pitch="-3st">
            나…<break time="200ms"/>가지…<break time="200ms"/>마…
        </prosody>
        
        <!-- 2) 쿨한 척 전환: 약간 빨라지고 음높이 살짝 올리기 -->
        <break time="300ms"/>
        <prosody rate="medium" pitch="+1st">
            …괜찮아. 그냥 가.
        </prosody>
        
        <!-- 3) 마지막으로 살짝 떨림 섞인 낮은 톤 -->
        <break time="150ms"/>
        <prosody rate="slow" pitch="-2st" volume="soft">
            (속삭이듯) 잘 지내…
        </prosody>
        </speak>

    """
    # 2) OpenAI TTS 호출 (SSML)
    payload = {
        "model": "tts-1-hd",        # 또는 "tts-1"
        "voice": "alloy",
        "input": ssml_template,
        "input_format": "ssml"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        content_type = resp.headers.get("Content-Type", "")
        if "audio" not in content_type:
            raise HTTPException(status_code=500, detail="Invalid response content type")

        # 파일명 생성 및 저장 (.mp3)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{timestamp}.mp3"
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "wb") as f:
            f.write(resp.content)

    # 저장된 파일 정보 반환
    return JSONResponse({"filename": filename, "path": path})

# 오디오 다운로드 엔드포인트
@app.get("/download/{filename}")
async def download_audio(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    # 미디어 타입은 mp3
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)

# =========================
# 실행 및 테스트 가이드
# =========================
# 1) 환경 변수 설정:
#    export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
#    (Windows PowerShell: $env:OPENAI_API_KEY="…")
#
# 2) uvicorn 서버 실행:
#    uvicorn main:app --reload --host 0.0.0.0 --port 8000
#
# 3) 오디오 생성 POST 요청 예시 (curl):
#    curl -X POST http://localhost:8000/generate-audio \
#      -H "Content-Type: application/json" \
#      -d '{
#            "script": "안녕하세요, 테스트 중입니다.",
#            "voice": "alloy"
#          }'
#
# 4) 오디오 다운로드 GET 요청 예시:
#    curl http://localhost:8000/download/{filename} --output downloaded.mp3
