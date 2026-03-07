import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

url = "https://www.businesspost.co.kr/BPView.php?res_no=384149"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # OpenGraph 이미지 확인
        og_image = soup.find('meta', property='og:image')
        if og_image:
            print(f"OG Image found: {og_image.get('content')}")
            
        # Twitter 이미지 확인
        twitter_image = soup.find('meta', name='twitter:image')
        if twitter_image:
            print(f"Twitter Image found: {twitter_image.get('content')}")
            
        # 본문 내 첫 번째 이미지 확인 (보통 /data/pub/... 경로)
        content_images = soup.select('div.view_con img') # 비즈니스포스트 본문 영역 추정
        if not content_images:
            content_images = soup.find_all('img')
            
        for img in content_images[:5]:
            src = img.get('src')
            if src:
                print(f"Found image src: {src}")
                abs_src = urljoin(url, src)
                
                # 도메인 결합 테스트 (상대경로 / 시작 시)
                parsed_url = urlparse(url)
                domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                domain_src = urljoin(domain, src)
                
                print(f"  Absolute (urljoin(url)): {abs_src}")
                print(f"  Absolute (urljoin(domain)): {domain_src}")

except Exception as e:
    print(f"Error: {e}")
