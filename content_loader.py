import chardet
import os
import re
import requests
import sys
from bs4 import BeautifulSoup
from langchain_community.document_loaders import YoutubeLoader
from urllib.parse import urlparse
from PyPDF2 import PdfReader
from utils import APIKeyManager, GeminiHandler

OUTPUT_DIR = 'output'
CONTENT_OUTPUT_FILE = 'retrieved_content.txt'

class WebScraper:
    @classmethod
    def scrape_website(cls, url: str) -> str:
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

        return GeminiHandler.generate_content(prompt)

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
        text_content = soup.get_text(separator=' ', strip=True)
        print(text_content[:10000])
        return WebScraper.format_amazon_product(text_content)

    @staticmethod
    def format_amazon_product(raw_product_info: str) -> str:
        prompt = f"""
以下はAmazon製品ページからスクレイピングした生の情報です。この情報を読みやすく整形してください。
以下の点に注意して整形を行ってください：

1. 製品タイトルを適切に強調する
2. 価格情報を明確に表示する
3. 製品説明を適切な段落に分ける
4. 特徴や機能を箇条書きで整理する
5. 重要な情報を強調し、冗長な部分を簡潔にする
6. 全体の構造を維持しつつ、読みやすさを向上させる

Amazon製品情報:
{raw_product_info}
        """
        return GeminiHandler.generate_content(prompt)

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
            raw_transcript = "\n".join([doc.page_content for doc in docs])
            return YouTubeHandler.format_transcript(raw_transcript)
        except Exception as e:
            print(f"YouTubeコンテンツの取得中にエラーが発生しました: {e}")
            return ""

    @staticmethod
    def format_transcript(raw_transcript: str) -> str:
        prompt = f"""
以下はYouTube動画の生のトランスクリプトです。このトランスクリプトを読みやすく整形してください。
以下の点に注意して整形を行ってください：

1. 適切な段落分けを行う
2. 句読点を適切に配置する
3. 明らかな文法エラーを修正する
4. 話者の変更がある場合は、新しい行で表示する
5. 冗長な繰り返しや言い間違いを削除する
6. 全体の流れを損なわない程度に、簡潔で明瞭な文章に整える

生のトランスクリプト:
{raw_transcript}
        """
        return GeminiHandler.generate_content(prompt)

class PDFHandler:
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return PDFHandler.format_pdf_text(text)

    @staticmethod
    def format_pdf_text(raw_text: str) -> str:
        prompt = f"""
以下はPDFから抽出した生のテキストです。このテキストを読みやすく整形してください。
以下の点に注意して整形を行ってください：

1. 適切な段落分けを行う
2. 句読点を適切に配置する
3. 見出しや小見出しを識別し、適切に強調する
4. 箇条書きや番号付きリストを適切に整形する
5. ページ番号や不要なヘッダー・フッター情報を削除する
6. 数式や表が含まれている場合は、可能な限り整形して読みやすくする
7. 全体の構造を維持しつつ、読みやすさを向上させる

PDFから抽出した生のテキスト:
{raw_text[:10000]}
        """
        return GeminiHandler.generate_content(prompt)

class ContentLoader:
    def __init__(self):
        self.api_key = APIKeyManager.get_api_key()
        GeminiHandler.initialize(self.api_key)

    def load_content(self, url_or_file: str) -> str:
        if url_or_file.startswith("http"):
            print(f"Scraping content from: {url_or_file}")
            if YouTubeHandler.is_youtube_url(url_or_file):
                content = YouTubeHandler.get_youtube_content(url_or_file)
            elif re.match(r'https?://(?:www\.)?github\.com/[\w-]+/[\w.-]+', url_or_file):
                content = WebScraper.extract_github_readme(url_or_file)
            elif WebScraper.is_amazon_url(url_or_file):
                content = WebScraper.scrape_amazon_product(url_or_file)
            else:
                content = WebScraper.scrape_website(url_or_file)
        else:
            print(f"Loading content from file: {url_or_file}")
            content = self.read_file_with_encoding(url_or_file)

        self.save_content(content)
        return content

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

    @staticmethod
    def save_content(content: str) -> None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        content_file = os.path.join(OUTPUT_DIR, CONTENT_OUTPUT_FILE)
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n取得したコンテンツが保存されました: {content_file}")

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
            {"url_or_file": "https://www.amazon.co.jp/dp/B00NTCH52W/"},
        ]

        for i, case in enumerate(test_cases):
            content = content_loader.load_content(case['url_or_file'])
            print(f"Content {i}: {content}")

if __name__ == "__main__":
    main()
