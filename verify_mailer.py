import re

# mailer.py에서 수정한 로직을 시뮬레이션
def clean_url(url_str):
    if not url_str: return None
    match = re.search(r'!?\[.*?\]\((https?://\S+?)\)', url_str)
    if match:
        url = match.group(1).rstrip(')]')
    else:
        url = url_str.strip('[]() *~_') # 마크다운 기호 제거
    
    if not url or url.lower() in ['none', 'null', 'n/a', '#']:
        return None
    return url

def process_summary_sim(text):
    text = text.replace('**', '')
    items = re.split(r'\n\s*\n|\n(?=\d+\.\s*제목:|\s*제목:)', text)
    results = []
    for item in items:
        if not item.strip(): continue
        
        img_match = re.search(r'(?:Image|이미지):\s*(\S+)', item, re.IGNORECASE)
        img_url = clean_url(img_match.group(1)) if img_match else None
        
        url_match = re.search(r'(?:URL|링크):\s*(\S+)', item, re.IGNORECASE)
        article_url = clean_url(url_match.group(1)) if url_match else "#"
        
        results.append({
            "img": img_url,
            "url": article_url
        })
    return results

# 테스트 케이스
test_text = """
**1. 제목: PCB 기술 혁신**
요약: 어쩌구 저쩌구
**3. URL:** https://example.com/news
**4. Image:** https://example.com/img.jpg

**1. 제목: 논문 요약**
요약: 논문 내용...
**3. URL:** **https://arxiv.org/pdf/123.456**
**4. Image:** None
"""

parsed = process_summary_sim(test_text)
for i, p in enumerate(parsed):
    print(f"Item {i+1}:")
    print(f"  Image: {p['img']}")
    print(f"  URL: {p['url']}")
