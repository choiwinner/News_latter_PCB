import requests
from newspaper import Article, Config
from urllib.parse import urljoin, urlparse

url = "https://www.businesspost.co.kr/BPView.php?res_no=384149"

config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'

article = Article(url, language='ko', config=config)
article.download()
article.parse()

print(f"Original Top Image: {article.top_image}")
og_image = article.meta_data.get('og', {}).get('image')
print(f"Original OG Image: {og_image}")

# 비즈니스포스트는 이미지 경로가 /data/pub/.. 식으로 시작하는 경우가 많음
# newspaper4k가 이를 어떻게 처리하는지 확인
img_url = article.top_image or og_image
if img_url:
    # 1. 단순 결합 테스트
    parsed_uri = urlparse(url)
    domain = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
    
    joined_1 = urljoin(url, img_url)
    joined_2 = urljoin(domain, img_url)
    
    print(f"Joined with URL: {joined_1}")
    print(f"Joined with Domain: {joined_2}")
    
    headers = {'User-Agent': config.browser_user_agent, 'Referer': url}
    
    for test_url in [joined_1, joined_2]:
        try:
            r = requests.head(test_url, headers=headers, timeout=5)
            print(f"Test {test_url} -> Status: {r.status_code}")
        except:
            print(f"Test {test_url} -> Failed")
