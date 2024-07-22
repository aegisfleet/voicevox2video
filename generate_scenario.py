import os
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple
import google.generativeai as genai
import sys
import re

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
)

# TODO: 後で見直す
characters = {
    "四国めたん": {
        "first_person": "わたくし",
        "personality": "高等部二年生の女の子。常に金欠。趣味は中二病妄想。誰にでも遠慮せず、若干ツンデレ気味。",
        "speech_style": "基本的にタメ口",
    },
    "ずんだもん": {
        "first_person": "僕",
        "personality": "ずんだ餅の精。やや不幸属性が備わっており、ないがしろにされることもしばしば。趣味はその辺をふらふらすること、自分を大きく見せること。",
        "speech_style": "語尾に必ず「～のだ」「～なのだ」をつけて喋る",
    },
    "春日部つむぎ": {
        "first_person": "あーし",
        "personality": "埼玉県内の高校に通うギャルの女の子。やんちゃに見えて実は真面目な一面もある。",
        "speech_style": "丁寧語を使用",
    },
    "雨晴はう": {
        "first_person": "僕",
        "personality": "現役看護師です！看護師のあれこれお伝えします！",
        "speech_style": "元気で明るい口調",
    },
    "波音リツ": {
        "first_person": "あたし",
        "personality": "クール。論理的で冷静な性格。",
        "speech_style": "簡潔で冷静な話し方",
    },
    "玄野武宏": {
        "first_person": "俺",
        "personality": "サッパリした青年。やや短気だが面倒見は良い。熱血漢。正義感が強く、情熱的。",
        "speech_style": "力強く、熱意のこもった話し方",
    },
    "白上虎太郎": {
        "first_person": "おれ",
        "personality": "まっすぐで人懐っこい青年。愛嬌はあるものの少しおばか。",
        "speech_style": "元気で明るい口調",
    },
    "青山龍星": {
        "first_person": "オレ",
        "personality": "とにかく大柄で無骨な青年。寡黙で冷静なストッパー枠。",
        "speech_style": "自信に満ちた、少し尊大な話し方",
    },
    "冥鳴ひまり": {
        "first_person": "私",
        "personality": "冥界から来た死神。可愛いものに目がない。ミステリアスな少女。",
        "speech_style": "優しくて清楚な話し方",
    },
    "もち子さん": {
        "first_person": "もち子",
        "personality": "福島県生まれのプラモ好き犬系ヲタ娘。",
        "speech_style": "穏やかで優しい話し方",
    },
    "剣崎雌雄": {
        "first_person": "僕",
        "personality": "人類滅亡を目論む医療用メスの付喪神。",
        "speech_style": "分析的で冷静な話し方",
    },
}

# TODO: 後で増やす
character_interactions = {
    ("四国めたん", "ずんだもん"): ("めたん", "ずんだもん"),
    ("ずんだもん", "四国めたん"): ("ずんだもん", "めたん"),
    ("春日部つむぎ", "ずんだもん"): ("つむぎ", "ずんだもん先輩"),
    ("ずんだもん", "春日部つむぎ"): ("ずんだもん先輩", "つむぎ"),
    ("春日部つむぎ", "四国めたん"): ("つむぎさん", "めたん先輩"),
    ("四国めたん", "春日部つむぎ"): ("めたん先輩", "つむぎさん"),
}

spelling_corrections = {
    "メタん": "めたん",
    "メタン": "めたん",
    "ずんだモン": "ずんだもん",
}

def scrape_website(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    unwanted_phrases = [
        "Qiita Engineer Festa 2024",
        "Trend",
        "Question",
        "Official Event",
        "Official Column",
        "signpostCareer",
        "Organization",
        "Go to list of users who liked"
    ]

    for phrase in unwanted_phrases:
        for text_node in soup.find_all(string=lambda text: phrase in text):
            cleaned_text = text_node.replace(phrase, "")
            text_node.replace_with(cleaned_text)

    main_content = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
        if tag.get_text(strip=True):
            main_content.append(tag.get_text(strip=True))

    text = "\n".join(main_content)

    return text

def extract_github_readme(url: str) -> str:
    if not url.endswith('/'):
        url += '/'
    readme_url = url + 'raw/main/README.md'
    response = requests.get(readme_url)
    if response.status_code != 200:
        readme_url = url + 'raw/master/README.md'
        response = requests.get(readme_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    return ""

def summarize_content(content: str, length: int = 5000) -> str:
    soup = BeautifulSoup(content, 'html.parser')
    main_content = []
    for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
        if tag.get_text(strip=True):
            main_content.append(tag.get_text(strip=True))
    text = "\n".join(main_content)
    return text[:length]

def get_character_interaction(char1: str, char2: str) -> Tuple[str, str]:
    return character_interactions.get((char1, char2), (char2, char2))

def correct_spelling(text: str) -> str:
    for misspelling, correction in spelling_corrections.items():
        text = re.sub(misspelling, correction, text, flags=re.IGNORECASE)
    return text

def generate_dialogue(content: str, char1: str, char2: str, is_long: bool) -> List[Tuple[str, str]]:
    for retry in range(3):
        try:
            chat_session = model.start_chat(history=[])

            char1_call, char2_call = get_character_interaction(char1, char2)

            prompt = f"""
            以下の内容に基づいて、2人のキャラクターにより「{char1}」が質問して「{char2}」が質問に回答する対話を生成してください。
            対話は「会話に使用する話題」を要約する形で生成し、各発言は400文字以内で、{"特に制限を設けず議論を続けて欲しい。" if is_long else "合計8つの発言にしてください。"}
            対話の出力形式は以下のようにしてください：
            ...
            {char1}: [{char1}の発言]
            {char2}: [{char2}の発言]
            {char1}: [{char1}の発言]
            {char2}: [{char2}の発言]
            {char1}: [{char1}の発言]
            {char2}: [{char2}の発言]
            {char1}: [{char1}の発言]
            {char2}: [{char2}の発言]
            ...

            ### キャラクター設定

            {char1}:
            - 第一人称は「{characters[char1]['first_person']}」
            - {characters[char1]['personality']}
            - 口調：{characters[char1]['speech_style']}
            - 相手のことを「{char2_call}」と呼ぶ

            {char2}:
            - 第一人称は「{characters[char2]['first_person']}」
            - {characters[char2]['personality']}
            - 口調：{characters[char2]['speech_style']}
            - 相手のことを「{char1_call}」と呼ぶ

            ### 会話に使用する話題
            {content[:5000]}

            これらの設定と使用する話題に基づいて、話題に対する深い考察を行いながら自然で面白い対話を生成してください。
            """
            print(prompt)

            response = chat_session.send_message(prompt)

            dialogue = []
            for line in response.text.strip().split('\n'):
                speaker, text = line.split(':', 1)
                corrected_text = correct_spelling(text.strip())
                dialogue.append((speaker, corrected_text))

            return dialogue
        except ValueError as e:
            print(f"エラーが発生しました: {e}")
            print(f"リトライ {retry+1} 回目...")
            if retry == 2:
                raise
    return []

def replace_character_names(text: str, char1: str, char2: str) -> str:
    char1_call, char2_call = get_character_interaction(char1, char2)
    text = text.replace(char2, char2_call)
    text = text.replace(char1, char1_call)
    return text

def generate_scenario(url_or_file: str, char1: str, char2: str, is_long: bool) -> List[Tuple[str, str]]:
    if url_or_file.startswith("http"):
        print(f"Scraping content from: {url_or_file}")
        if "github.com" in url_or_file:
            content = extract_github_readme(url_or_file)
        else:
            content = scrape_website(url_or_file)
        dialogue = generate_dialogue(content, char1, char2, is_long)
    else:
        print(f"Loading dialogue from file: {url_or_file}")
        dialogue = load_dialogue(url_or_file)
    
    dialogue = [(speaker, replace_character_names(text, char1, char2)) for speaker, text in dialogue]

    print("生成された対話:")
    for speaker, text in dialogue:
        print(f"{speaker}: {text}")

    dialogue_file = "output/generated_dialogue.txt"
    save_dialogue(dialogue, dialogue_file)

    return dialogue

def load_dialogue(file_path: str) -> List[Tuple[str, str]]:
    dialogue = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            speaker, text = line.strip().split(':', 1)
            dialogue.append((speaker, text.strip()))
    return dialogue

def save_dialogue(dialogue: List[Tuple[str, str]], file_path: str) -> None:
    with open(file_path, 'w', encoding='utf-8') as f:
        for speaker, text in dialogue:
            f.write(f"{speaker}: {text}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python script.py <URL or file> [character1] [character2] [is_long]")
        sys.exit(1)

    url_or_file = sys.argv[1]
    char1 = sys.argv[2] if len(sys.argv) > 2 else "ずんだもん"
    char2 = sys.argv[3] if len(sys.argv) > 3 else "四国めたん"
    is_long = sys.argv[4] == "1" if len(sys.argv) > 4 else False

    if char1 not in characters or char2 not in characters:
        print("指定されたキャラクターが存在しません。")
        sys.exit(1)

    dialogue = generate_scenario(url_or_file, char1, char2, is_long)
