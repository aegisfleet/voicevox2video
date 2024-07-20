import os
import requests
from bs4 import BeautifulSoup, Comment
from typing import List, Tuple
import google.generativeai as genai
import re

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
)

def scrape_website(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    main_content = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
        if tag.get_text(strip=True):
            main_content.append(tag.get_text(strip=True))

    text = "\n".join(main_content)

    return text

def extract_github_readme(url: str) -> str:
    if not url.endswith('/'):
        url += '/'
    readme_url = url + 'raw/master/README.md'
    response = requests.get(readme_url)
    if response.status_code != 200:
        readme_url = url + 'raw/main/README.md'
        response = requests.get(readme_url)
    if response.status_code == 200:
        return response.text
    return ""

def summarize_content(content: str, length: int = 5000) -> str:
    soup = BeautifulSoup(content, 'html.parser')
    main_content = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
        if tag.get_text(strip=True):
            main_content.append(tag.get_text(strip=True))
    text = "\n".join(main_content)
    return text[:length]

def generate_dialogue(content: str) -> List[Tuple[int, str]]:
    for retry in range(3):
        try:
            chat_session = model.start_chat(history=[])
            print(content[:5000])

            prompt = f"""
            以下の内容に基づいて、2人のキャラクターにより「ずんだもん」が質問して「四国めたん」が質問に回答する対話を生成してください。
            対話は「会話に使用する話題」を要約する形で生成し、各発言は400文字以内で、合計8つの発言にしてください。
            対話の形式は以下のようにしてください：
            1: [ずんだもんの発言]
            0: [四国めたんの発言]
            1: [ずんだもんの発言]
            0: [四国めたんの発言]
            1: [ずんだもんの発言]
            0: [四国めたんの発言]
            1: [ずんだもんの発言]
            0: [四国めたんの発言]

            ### キャラクター設定

            ずんだもん:
            - ずんだ餅の精。第一人称はボクまたはずんだもん
            - やや不幸属性が備わっており、ないがしろにされることもしばしば
            - 趣味はその辺をふらふらすること、自分を大きく見せること
            - 口調：不自然な日本語にならない限り、語尾に必ず「～のだ」「～なのだ」をつけて喋る
            - 相手のことを「めたん」と呼ぶ
            - あまり知識がないが好奇心旺盛

            四国めたん:
            - 高等部二年生の女の子。第一人称はわたくし
            - 常に金欠。趣味は中二病妄想
            - 誰にでも遠慮せず、若干ツンデレ気味
            - 口調：基本的にタメ口
            - 相手のことを「ずんだもん」と呼ぶ
            - 色々なことを知っている

            ### 会話に使用する話題
            {content[:5000]}

            これらの設定と使用する話題に基づいて、話題に対する深い考察を行いながら自然で面白い対話を生成してください。
            """

            response = chat_session.send_message(prompt)

            dialogue = []
            for line in response.text.strip().split('\n'):
                speaker, text = line.split(':', 1)
                dialogue.append((int(speaker), text.strip()))

            return dialogue
        except ValueError as e:
            print(f"エラーが発生しました: {e}")
            print(f"リトライ {retry+1} 回目...")
            if retry == 2:
                raise
    return []

def replace_metan(text: str) -> str:
    return re.sub(r'メタん', 'めたん', text)

def scrape_and_generate(url_or_file: str) -> List[Tuple[int, str]]:
    if url_or_file.startswith("http"):
        print(f"Scraping content from: {url_or_file}")
        if "github.com" in url_or_file:
            content = extract_github_readme(url_or_file)
        else:
            content = scrape_website(url_or_file)
        dialogue = generate_dialogue(content)
    else:
        print(f"Loading dialogue from file: {url_or_file}")
        dialogue = load_dialogue(url_or_file)
    
    return [(speaker, replace_metan(text)) for speaker, text in dialogue]

def load_dialogue(file_path: str) -> List[Tuple[int, str]]:
    dialogue = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            speaker, text = line.strip().split(':', 1)
            dialogue.append((int(speaker == "ずんだもん"), text.strip()))
    return dialogue

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url_or_file = sys.argv[1]
        dialogue = scrape_and_generate(url_or_file)
        print("生成された対話:")
        for speaker, text in dialogue:
            character_name = "四国めたん" if speaker == 0 else "ずんだもん"
            print(f"{character_name}: {text}")
    else:
        print("URLまたはファイルパスを指定してください。")
