import re

def clean_url(url_str):
    if not url_str: return None
    url = url_str.strip('[]() *~_')
    if not url or url.lower() in ['none', 'null', 'n/a', '#']:
        return None
    return url

def process_summary_sim(text):
    text = text.replace('**', '')
    items = re.split(r'\n\s*\n|\n(?=\d+\.\s*제목:|\s*제목:)', text)
    results = []
    for item in items:
        if not item.strip(): continue
        
        url_match = re.search(r'(?:URL|링크):\s*(\S+)', item, re.IGNORECASE)
        article_url = clean_url(url_match.group(1)) if url_match else None
        
        has_link = True if article_url else False
        results.append({
            "has_link": has_link,
            "url": article_url
        })
    return results

# 테스트 케이스
test_text = """
공신력 있는 전문가로서 서평을 시작합니다. (인트로 문구)

**1. 제목: 진짜 뉴스**
요약: 내용
URL: https://example.com/ok

**2. 제목: URL 없는 항목**
요약: 이 항목은 링크가 없습니다.
"""

parsed = process_summary_sim(test_text)
for i, p in enumerate(parsed):
    print(f"Item {i+1}:")
    print(f"  Has Link: {p['has_link']}")
    print(f"  URL: {p['url']}")
