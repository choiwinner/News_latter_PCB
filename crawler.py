import feedparser
import arxiv
from datetime import datetime, timedelta
import urllib.parse
from newspaper import Article, Config
from googlenewsdecoder import gnewsdecoder
import logging
import requests
import nltk
import time
import random

# NLTK 리소스 다운로드 (GitHub Actions 등 클린 환경 대응)
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

# newspaper4k 설정 (타임아웃 등)
config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
config.request_timeout = 10

# newspaper4k 로그 레벨 조정 (불필요한 로그 방지)
logging.getLogger('newspaper').setLevel(logging.ERROR)

def resolve_google_news_url(url):
    """
    Google 뉴스 RSS URL을 디코딩하여 원본 기사 주소를 반환합니다.
    """
    try:
        # 1. googlenewsdecoder 시도
        result = gnewsdecoder(url)
        if result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
        
        # 2. 실패 시 requests로 리디렉션 추적 (일부 케이스 대응)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=5)
        if response.url and "google.com" not in response.url:
            return response.url
            
        return url
    except Exception as e:
        print(f"URL 디코딩 실패: {e}")
        return url

def get_article_image(url, retries=2, delay=1.5):
    """
    newspaper4k 및 메타데이터를 사용하여 기사 URL에서 주요 이미지 URL을 추출합니다.
    실패 시 재시도 로직을 포함합니다.
    """
    for attempt in range(retries + 1):
        try:
            if "google.com" in url and "rss/articles" not in url:
                return None
                
            article = Article(url, language='ko', config=config)
            article.download()
            
            # 다운로드 실패 시 재시도
            if not article.html or len(article.html) < 200:
                raise Exception("HTML 내용이 너무 짧거나 비어 있음")
                
            article.parse()
            
            # 1. newspaper4k의 기본 top_image 시도
            image = article.top_image
            
            # 2. 실패 시 OpenGraph 또는 Twitter 메타데이터 직접 확인
            if not image or "googleusercontent.com" in image or "gstatic.com" in image:
                image = article.meta_data.get('og', {}).get('image')
                if not image:
                    image = article.meta_data.get('twitter', {}).get('image')
            
            # 3. 절대 경로 확인 및 구글 서버 이미지 필터링
            if image:
                if not image.startswith('http'):
                    from urllib.parse import urljoin
                    image = urljoin(url, image)
                    
                if "googleusercontent.com" in image or "gstatic.com" in image:
                    return None
                
                # 이미지 URL이 유효한지 가볍게 확인 (헤더만)
                try:
                    img_check = requests.head(image, headers={'User-Agent': config.browser_user_agent, 'Referer': url}, timeout=5)
                    if img_check.status_code != 200:
                        # 404 등의 경우 다시 한 번 GET 시도 (일부 서버 대응)
                        img_check = requests.get(image, headers={'User-Agent': config.browser_user_agent, 'Referer': url}, timeout=5, stream=True)
                        if img_check.status_code != 200:
                            image = None
                except:
                    pass
            
            if image:
                return image
            
            # 이미지를 찾지 못한 경우 잠시 대기 후 재시도
            if attempt < retries:
                time.sleep(delay)
                
        except Exception as e:
            if attempt < retries:
                time.sleep(delay * (attempt + 1)) # 점진적 대기
                continue
            print(f"이미지 추출 최종 실패 ({url}): {e}")
            
    return None

def filter_relevant_news(items, keywords_str, top_n=10):
    """
    제목 및 출처를 기반으로 뉴스 기사의 관련성을 점수화하고 중복을 제거하여 상위 n개를 선별합니다.
    """
    # 1. 신뢰도 높은 출처 목록 (가중치 부여)
    REPUTABLE_SOURCES = [
        "전자신문", "ZDNet", "지디넷", "디지털데일리", "디데일리", "테크월드", "헬로티", 
        "매일경제", "한국경제", "EE Times", "Digitimes", "Reuters", "Bloomberg", "Forbes"
    ]
    
    # 2. 관련 핵심 키워드 (가중치 부여용)
    core_keywords = ["PCB", "인쇄회로기판", "패키징", "packaging", "서브스트레이트", "substrate", "기판", "반도체", "HBM"]
    
    scored_items = []
    seen_titles = [] # 중복 제거용 (제목 유사성 기반)

    for item in items:
        title = item.get("title", "").strip()
        source = item.get("source", "")
        
        # 3. 간단한 중복 제거 (완전 일치 또는 매우 유사한 제목 제외)
        # 제목에서 특수문자 제거 후 비교
        clean_title = "".join(e for e in title if e.isalnum())
        is_duplicate = False
        for seen in seen_titles:
            # 제목이 80% 이상 겹치면 중복으로 간주
            if len(clean_title) > 0 and (clean_title in seen or seen in clean_title):
                is_duplicate = True
                break
        
        if is_duplicate:
            continue
        
        # 4. 점수 계산
        score = 0
        
        # 키워드 점수
        for kw in core_keywords:
            if kw.lower() in title.lower():
                score += 5
        
        # 출처 점수
        for rep in REPUTABLE_SOURCES:
            if rep.lower() in source.lower() or rep.lower() in title.lower():
                score += 10
                
        scored_items.append((score, item))
        seen_titles.append(clean_title)

    # 점수 높은 순으로 정렬
    scored_items.sort(key=lambda x: x[0], reverse=True)
    
    return [x[1] for x in scored_items[:top_n]]

def get_google_news(keywords, days=7, max_results=10):
    """
    구글 뉴스 RSS를 통해 키워드 관련 뉴스를 가져옵니다.
    효율성을 위해 먼저 제목을 필터링한 후 상세 정보(이미지 등)를 추출합니다.
    """
    base_url = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    query = f"{keywords} when:{days}d"
    encoded_query = urllib.parse.quote(query)
    rss_url = base_url.format(query=encoded_query)
    
    feed = feedparser.parse(rss_url)
    
    # 1. 먼저 RSS에서 제공하는 기본 정보만 수집 (최대 30개)
    initial_items = []
    for entry in feed.entries[:30]:
        initial_items.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "source": entry.source.get("title", "Google News") if hasattr(entry, "source") else "Google News"
        })
    
    # 2. 관련성 및 중복 제거 필터링 적용 (원하는 결과 수의 1.2배 정도를 먼저 선별)
    filtered_items = filter_relevant_news(initial_items, keywords, top_n=int(max_results * 1.2))
    
    # 3. 선별된 아이템들에 대해서만 상세 정보(원본 URL, 이미지) 추출
    results = []
    for item in filtered_items:
        if len(results) >= max_results:
            break
            
        decoded_url = resolve_google_news_url(item["link"])
        time.sleep(random.uniform(0.5, 1.5)) # 지연 단축 (이미 필터링됨)
        
        image_url = get_article_image(decoded_url)
        
        results.append({
            "title": item["title"],
            "link": decoded_url,
            "published": item["published"],
            "source": item["source"],
            "image_url": image_url
        })
        
    return results

def get_arxiv_papers(keywords, max_results=5, max_retries=3):
    """
    arXiv API를 통해 관련 논문을 가져옵니다.
    """
    search = arxiv.Search(
        query=keywords,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    for attempt in range(max_retries):
        try:
            results = []
            for result in search.results():
                # 최근 7일 이내 논문인지 확인 (필요시 조절)
                results.append({
                    "title": result.title,
                    "link": result.entry_id,
                    "published": result.published.strftime("%Y-%m-%d"),
                    "summary": result.summary, # LLM 요약을 위해 원문 요약 포함
                    "source": "arXiv"
                })
            return results
        except arxiv.HTTPError as e:
            if attempt < max_retries - 1:
                delay = (2 ** (attempt + 1)) + random.uniform(0, 1)
                print(f"arXiv API 접속 오류 ({e}). {delay:.1f}초 후 재시도... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"arXiv API 최종 실패: {e}")
                return []
        except Exception as e:
            print(f"arXiv API 논문 수집 중 알 수 없는 오류 발생: {e}")
            return []
            
    return []

if __name__ == "__main__":
    # 간단한 테스트
    print("--- Google News Test (HBM) ---")
    news = get_google_news("HBM 메모리 반도체", days=7)
    for n in news[:3]:
        print(f"[{n['published']}] {n['title']}\nURL: {n['link']}\n")
        
    print("\n--- arXiv Paper Test (High Bandwidth Memory) ---")
    papers = get_arxiv_papers("High Bandwidth Memory", max_results=3)
    for p in papers:
        print(f"[{p['published']}] {p['title']}\nURL: {p['link']}\n")
