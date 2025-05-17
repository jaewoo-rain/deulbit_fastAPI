from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

# 1) 토크나이저·모델 다운로드·캐시
MODEL_ID = "canopylabs/3b-ko-ft-research_release"
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16
)

# GPU가 하나뿐이라면:
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
model.eval()

# 이후 TTS 파이프라인에 model/tokenizer 넘기기
from transformers import pipeline
tts = pipeline(
    "text-to-speech",
    model=model,
    tokenizer=tokenizer,
    torch_dtype=torch.float16,
    device=device,    # pipeline은 device 인덱스(정수) 또는 torch.device 둘 다 지원
    token=True
)
