from google import genai
from google.genai import errors
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

import time

# RPM 제한을 위한 마지막 호출 시간 기록
last_call_time = 0

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((errors.ClientError, errors.ServerError)),
    reraise=True
)
def generate_content_with_retry(client, model_name, prompt):
    """
    할당량 초과(429) 시 재시도를 포함하여 콘텐츠를 생성합니다.
    분당 요청 제한(RPM 5)을 위해 호출 전 대기 시간을 가집니다.
    """
    global last_call_time
    
    # 마지막 호출로부터 최소 15초(RPM 4 목표)가 경과했는지 확인
    elapsed = time.time() - last_call_time
    if elapsed < 15:
        wait_time = 15 - elapsed
        print(f"RPM 제한을 위해 {wait_time:.1f}초 대기 중...")
        time.sleep(wait_time)
        
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        last_call_time = time.time() # 성공적으로 호출한 시간 기록
        return response.text
    except (errors.ClientError, errors.ServerError) as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "503" in str(e) or "UNAVAILABLE" in str(e):
            print(f"API 이슈(429/503). 재시도 중... ({e})")
            raise e
        raise e

def summarize_content(items, category="뉴스"):
    """
    수집된 항목들을 최신 google.genai SDK를 사용하여 요약합니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "API 키가 설정되지 않았습니다."
    
    client = genai.Client(api_key=api_key)
    
    # gemini-3-flash는 현재 하루 20회 요청으로 제한이 매우 엄격합니다.
    # 성능이 뛰어나고 할당량(분당 15회)이 더 넉넉한 gemini-2.0-flash를 사용합니다.
    model_name = "gemini-3.5-flash"
    # model_name = "gemini-3-flash-preview" 
    # model_name = "gemini-2.5-flash-lite"

    prompt = f"""
    당신은 PCB(인쇄회로기판), 반도체 패키징 및 고밀도 상호연결 기술 전문가입니다. 
    제공된 {category} 목록을 바탕으로, 전문적인 기술 통향이 담긴 주간 브리핑을 작성해 주세요.
    
    각 항목에 대해 다음 형식을 엄격히 지켜주세요:
    1. 제목: [기사/논문의 핵심 기술 키워드를 포함한 전문적인 한글 제목]
    2. 요약: [공신력 있는 정보를 바탕으로, 기술적 특징과 파급력을 2-3문장으로 핵심 분석 요약]
    3. URL: [제공된 원본 URL을 마크다운 형식 없이 순수하게 문자열로만 적어주세요.]
    4. Image: [제공된 image_url이 있다면 순수 URL만 적어주세요. 없다면 'None'.]

    중요 지침:
    - 기술적 정확성과 전문성을 최우선으로 하세요. 
    - 중복된 정보는 지양하고, 기술적 가치가 높은 소식을 우선 선정하여 분석하세요.
    - 대상 기사가 기술적으로 중요한 내용을 담고 있다면 이를 구체적으로 명시하세요.
    - URL과 Image 항목에는 마크다운 형식을 절대 사용하지 마세요.
    
    대상 데이터:
    {items}
    """
    
    try:
        return generate_content_with_retry(client, model_name, prompt)
    except Exception as e:
        return f"요약 생성 중 오류 발생: {e}"

if __name__ == "__main__":
    # 테스트 코드
    test_items = [
        {"title": "SK Hynix sample HBM4 to NVIDIA", "link": "https://example.com/1", "image_url": "https://example.com/img1"},
        {"title": "Samsung Electronics develops 12-layer HBM3E", "link": "https://example.com/2", "image_url": "https://example.com/img2"}
    ]
    if os.getenv("GEMINI_API_KEY"):
        print(summarize_content(test_items))
    else:
        print("GEMINI_API_KEY가 .env 파일에 없습니다.")
