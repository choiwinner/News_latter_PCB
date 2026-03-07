import requests
from newspaper import Article, Config
from urllib.parse import urljoin, quote, urlparse
import logging

# newspaper4k 로그 끄기
logging.getLogger('newspaper').setLevel(logging.ERROR)

def test_url(url):
    print(f"\n--- Testing URL: {url} ---")
    config = Config()
    config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    config.request_timeout = 10

    try:
        article = Article(url, language='ko', config=config)
        article.download()
        article.parse()
        
        print(f"Top Image: {article.top_image}")
        og_image = article.meta_data.get('og', {}).get('image')
        print(f"OG Image: {og_image}")
        
        img_url = article.top_image or og_image
        
        if img_url:
            if not img_url.startswith('http'):
                img_url = urljoin(url, img_url)
            
            print(f"Final Image URL: {img_url}")
            
            # 이미지 실제 존재 여부 확인
            headers = {
                'User-Agent': config.browser_user_agent,
                'Referer': url
            }
            resp = requests.get(img_url, headers=headers, timeout=5)
            print(f"Image HTTP Status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Reason: {resp.reason}")
                if "Not Found" in resp.text:
                    print("Detected 'Not Found' in response body")
        else:
            print("No image found by newspaper4k")

    except Exception as e:
        print(f"Error during processing: {e}")

# 비즈니스포스트 예시 URL
test_url("https://www.businesspost.co.kr/BPView.php?res_no=384149")
