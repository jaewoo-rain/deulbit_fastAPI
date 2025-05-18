from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
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

class DownloadRequest(BaseModel):
    fileName: str
    index: int  # -1 이면 합본, 그 외엔 개별 파일 인덱스

@app.post("/generate-audio")
async def generate_audio(requests: List[TTSRequest]):
    """
    여러 개의 TTSRequest를 받아서,
    1) 개별 MP3 파일을 fileName{index}.mp3 로 저장
    2) 모두 바이너리 이어 붙여 fileName_combined.mp3 로 저장
    3) [{"path": "...", "combined": "..."}] 형태로 반환
    """
    if not requests:
        raise HTTPException(status_code=400, detail="요청 리스트가 비어 있습니다.")

    base_name = requests[0].fileName
    out_dir = os.path.join(OUTPUT_DIR, base_name)
    os.makedirs(out_dir, exist_ok=True)

    temp_paths: List[str] = []
    temp_contents: List[bytes] = []

    async with httpx.AsyncClient() as client:
        for idx, req in enumerate(requests):
            # multipart/form-data 바디 구성
            url = "https://www.openai.fm/api/generate"
            boundary = "----WebKitFormBoundarya027BOtfh6crFn7A"
            body_lines = []
            for field_name, val in [
                ("input", req.script),
                ("voice", req.voice.lower()),
                ("vibe", req.vibeKey),
                ("prompt", req.vibePrompt),
            ]:
                body_lines.append(f"--{boundary}")
                body_lines.append(f'Content-Disposition: form-data; name="{field_name}"\r\n')
                body_lines.append(val)
            body_lines.append(f"--{boundary}--")
            body = "\r\n".join(body_lines).encode("utf-8")

            headers = {
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Origin": "https://www.openai.fm",
                "User-Agent": "fastapi-tts-client"
            }

            # API 호출
            resp = await client.post(url, headers=headers, content=body)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            ctype = resp.headers.get("Content-Type", "")
            if "mpeg" not in ctype and "mp3" not in ctype:
                raise HTTPException(status_code=500, detail=f"Unsupported content type: {ctype}")

            # 개별 MP3 저장
            filename = f"{base_name}{idx}.mp3"
            file_path = os.path.join(out_dir, filename)
            with open(file_path, "wb") as f:
                f.write(resp.content)
            temp_paths.append(file_path)
            temp_contents.append(resp.content)

    # 바이너리 이어붙여 합본 생성
    combined_name = f"{base_name}_combined.mp3"
    combined_path = os.path.join(out_dir, combined_name)
    with open(combined_path, "wb") as outf:
        for chunk in temp_contents:
            outf.write(chunk)

    # return JSONResponse([{
    #     "path": out_dir,
    #     "combined": combined_name
    # }])

    return FileResponse(
        path=combined_path,
        media_type="audio/mp3",
        filename=combined_name
    )


@app.post("/download-audio")
async def download_audio(req: DownloadRequest):
    """
    fileName 폴더 안에서 index에 따라
    - index >= 0: fileName{index}.mp3
    - index < 0:  fileName_combined.mp3
    를 찾아서 내려줍니다.
    """
    dir_path = os.path.join(OUTPUT_DIR, req.fileName)
    if req.index < 0:
        filename = f"{req.fileName}_combined.mp3"
    else:
        filename = f"{req.fileName}{req.index}.mp3"

    file_path = os.path.abspath(os.path.join(dir_path, filename))
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"파일이 없습니다: {file_path}")

    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename
    )
