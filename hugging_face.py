# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("canopylabs/3b-ko-ft-research_release")
model = AutoModelForCausalLM.from_pretrained("canopylabs/3b-ko-ft-research_release")

model.eval()

# 입력 프롬프트
prompt = "안녕하세요. 오늘 서울 날씨를 알려주세요."

# 토크나이징
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

# 생성
outputs = model.generate(
    **inputs,
    max_new_tokens=100,
    do_sample=True,
    top_k=50,
    temperature=0.8,
    eos_token_id=tokenizer.eos_token_id
)

# 디코딩
generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(generated)