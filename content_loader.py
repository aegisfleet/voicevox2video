import chardet
import google.generativeai as genai
import os
import re
import requests
import sys
from bs4 import BeautifulSoup
from langchain_community.document_loaders import YoutubeLoader
from urllib.parse import urlparse
from PyPDF2 import PdfReader

API_KEY_FILE = '.gemini_api_key'

class APIKeyManager:
    @staticmethod
    def get_api_key() -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            try:
                with open(API_KEY_FILE, 'r') as f:
                    api_key = f.read().strip()
            except FileNotFoundError:
                raise SystemExit(f"エラー: GEMINI_API_KEY環境変数が設定されておらず、{API_KEY_FILE}ファイルも見つかりません。")
        if not api_key:
            raise SystemExit("エラー: API キーが見つかりません。")
        return api_key

class WebScraper:
    @classmethod
    def initialize(cls, api_key: str):
        genai.configure(api_key=api_key)
        cls.model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    @classmethod
    def scrape_website(cls, url: str) -> str:
        if not hasattr(cls, 'model'):
            raise RuntimeError("WebScraper が初期化されていません。まず WebScraper.initialize(api_key) を呼び出してください。")

        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)
        print(text_content[:10000])

        prompt = f"""
以下のテキストはWebページの生のコンテンツです。
主要なコンテンツを抽出してください。
主要な情報に重点を置き、ナビゲーションメニュー、広告、フッター情報などの無関係な部分は削除してください。
元の構造と重要な詳細を維持してください。

Webページのコンテンツ:
{text_content[:10000]}
        """

        response = cls.model.generate_content(prompt)
        
        if response.text:
            return response.text.strip()
        else:
            return "コンテンツの抽出に失敗しました。"

    @staticmethod
    def extract_github_readme(url: str) -> str:
        github_pattern = r'https?://(?:www\.)?github\.com/[\w-]+/[\w.-]+'
        
        if not re.match(github_pattern, url):
            return ""

        for branch in ['main', 'master']:
            for filename in ['README.md', 'README.rst']:
                readme_url = f"{url.rstrip('/')}/raw/{branch}/{filename}"
                response = requests.get(readme_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    lines = [line.strip() for line in soup.get_text().split('\n')]
                    return '\n'.join(line for line in lines if line and not line.startswith('```'))
        return ""

    @staticmethod
    def is_amazon_url(url: str) -> bool:
        parsed_url = urlparse(url)
        return parsed_url.netloc in ['amazon.com', 'www.amazon.com', 'amazon.co.jp', 'www.amazon.co.jp', 'amzn.to']

    @staticmethod
    def scrape_amazon_product(url: str) -> str:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        title = soup.find('span', {'id': 'productTitle'})
        price = soup.find('span', {'class': 'a-price-whole'})
        description = soup.find('div', {'id': 'productDescription'})
        features = soup.find('div', {'id': 'feature-bullets'})

        product_info = []
        if title:
            product_info.append(f"Title: {title.text.strip()}")
        if price:
            product_info.append(f"Price: {price.text.strip()}")
        if description:
            product_info.append(f"Description: {description.text.strip()}")
        if features:
            product_info.append("Features:")
            for li in features.find_all('li'):
                product_info.append(f"- {li.text.strip()}")

        return "\n".join(product_info)

class YouTubeHandler:
    @staticmethod
    def is_youtube_url(url: str) -> bool:
        try:
            parsed_url = urlparse(url)
            return parsed_url.netloc in ['youtube.com', 'www.youtube.com', 'youtu.be'] or parsed_url.path.startswith('/shorts/')
        except ValueError:
            return False

    @staticmethod
    def get_youtube_content(url: str) -> str:
        try:
            loader = YoutubeLoader.from_youtube_url(url, language=["en", "ja"])
            docs = loader.load()
            return "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            print(f"YouTubeコンテンツの取得中にエラーが発生しました: {e}")
            return ""

class PDFHandler:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return PDFHandler.clean_pdf_text(text)

    @staticmethod
    def clean_pdf_text(text: str) -> str:
        text = re.sub(r'\n\s*-?\s*\d+\s*-?\s*\n', '\n', text)
        text = re.sub(r'\n\s*Page\s*\d+\s*\n', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?<![.!?。！？])\n(?=[a-zぁ-ん])', ' ', text)
        text = re.sub(r'^\s*[●○・]\s*', '\n• ', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*(\d+)[.．、]\s*', r'\n\1. ', text, flags=re.MULTILINE)
        text = re.sub(r'^([A-Z0-9][A-Z0-9 ]+)$', r'\n\n## \1\n', text, flags=re.MULTILINE)
        text = re.sub(r'([a-zA-Z0-9])([+\-*/=])', r'\1 \2 ', text)
        text = re.sub(r'([+\-*/=])([a-zA-Z0-9])', r' \1 \2', text)
        text = text.strip()

        return text

class ContentLoader:
    def __init__(self):
        self.api_key = self.get_api_key()
        WebScraper.initialize(self.api_key)

    @staticmethod
    def get_api_key() -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            try:
                with open(API_KEY_FILE, 'r') as f:
                    api_key = f.read().strip()
            except FileNotFoundError:
                raise SystemExit(f"エラー: GEMINI_API_KEY環境変数が設定されておらず、{API_KEY_FILE}ファイルも見つかりません。")
        if not api_key:
            raise SystemExit("エラー: API キーが見つかりません。")
        return api_key

    def load_content(self, url_or_file: str) -> str:
        if url_or_file.startswith("http"):
            print(f"Scraping content from: {url_or_file}")
            if YouTubeHandler.is_youtube_url(url_or_file):
                return YouTubeHandler.get_youtube_content(url_or_file)
            elif re.match(r'https?://(?:www\.)?github\.com/[\w-]+/[\w.-]+', url_or_file):
                return WebScraper.extract_github_readme(url_or_file)
            elif WebScraper.is_amazon_url(url_or_file):
                return WebScraper.scrape_amazon_product(url_or_file)
            else:
                return WebScraper.scrape_website(url_or_file)
        else:
            print(f"Loading content from file: {url_or_file}")
            return self.read_file_with_encoding(url_or_file)

    @staticmethod
    def read_file_with_encoding(file_path: str) -> str:
        if file_path.lower().endswith('.pdf'):
            return PDFHandler.extract_text_from_pdf(file_path)
        
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        encoding = chardet.detect(raw_data)['encoding']
        try:
            return raw_data.decode(encoding)
        except UnicodeDecodeError:
            print(f"警告: {encoding}でのデコードに失敗しました。UTF-8で再試行します。")
            return raw_data.decode('utf-8')

def main():
    content_loader = ContentLoader()

    if len(sys.argv) > 1:
        url_or_file = sys.argv[1]
        content = content_loader.load_content(url_or_file)
        print(f"Content:\n{content}")
    else:
        test_cases = [
            {"url_or_file": "scenario/generated_dialogue_sample.txt"},
            {"url_or_file": "README.md"},
            {"url_or_file": "scenario/demo.pdf"},
            {"url_or_file": "https://www.yahoo.co.jp/"},
            {"url_or_file": "https://github.com/aegisfleet/voicevox2video"},
            {"url_or_file": "https://youtu.be/oWGPJ7PHB8w"},
            {"url_or_file": "https://www.amazon.co.jp/dp/B00NTCH52W"},
        ]

        for i, case in enumerate(test_cases):
            content = content_loader.load_content(case['url_or_file'])
            print(f"Content {i}: {content}")

if __name__ == "__main__":
    main()
