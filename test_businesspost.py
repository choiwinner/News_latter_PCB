import requests
from newspaper import Article, Config
from urllib.parse import urljoin

url = "https://www.businesspost.co.kr/BPView.php?res_no=384149" # 예시 URL

config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

try:
    article = Article(url, language='ko', config=config)
    article.download()
    article.parse()
    
    print(f"Top Image: {article.top_image}")
    print(f"Meta Image: {article.meta_data.get('og', {}).get('image')}")
    
    # 이미지 URL이 유효한지 체크
    img_url = article.top_image
    if img_url:
        if not img_url.startswith('http'):
            img_url = urljoin(url, img_url)
        
        headers = {'User-Agent': config.browser_user_agent, 'Referer': url}
        resp = requests.head(img_url, headers=headers, timeout=5)
        print(f"Image Check (HEAD) {img_url}: {resp.status_code}")
        
        resp_get = requests.get(img_url, headers=headers, timeout=5)
        print(f"Image Check (GET) {img_url}: {resp_get.status_code}")
        if resp_get.status_code != 200:
            print("Content:", resp_get.text[:200])

except Exception as e:
    print(f"Error: {e}")
