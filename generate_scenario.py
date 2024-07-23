import os
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple
import google.generativeai as genai
import sys
import re

def load_json_config(filename):
    config_path = os.path.join('config', filename)
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

characters = load_json_config('characters.json')
character_interactions = load_json_config('character_interactions.json')

spelling_corrections = {
    "メタん": "めたん",
    "メタン": "めたん",
    "ずんだモン": "ずんだもん",
    "なのだな？": "なのだ？",
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

        lines = [line.strip() for line in text.split('\n')]

        inside_code_block = False
        filtered_lines = []
        for line in lines:
            if line.startswith('```'):
                inside_code_block = not inside_code_block
            elif not inside_code_block and line:
                filtered_lines.append(line)

        return '\n'.join(filtered_lines)
    return ""

def get_character_interaction(char1: str, char2: str) -> Tuple[str, str]:
    key = f"{char1},{char2}"
    return character_interactions.get(key, (char2, char2))

def correct_spelling(text: str) -> str:
    for misspelling, correction in spelling_corrections.items():
        text = re.sub(misspelling, correction, text, flags=re.IGNORECASE)
    return text

def generate_dialogue(content: str, char1: str, char2: str, mode: int) -> List[Tuple[str, str]]:
    try:
        api_key = os.environ["GEMINI_API_KEY"]
    except KeyError:
        raise SystemExit("エラー: GEMINI_API_KEY環境変数が設定されているか確認してください。")

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
    )

    for retry in range(3):
        try:
            chat_session = model.start_chat(history=[])

            char1_call, char2_call = get_character_interaction(char1, char2)

            prompt = f"""
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

            これらの設定と会話に使用する話題に基づいて、{"話題に対する深い考察を行いながら自然で面白い" if mode in [1, 2] else "話題の内容を正確に説明するための"}対話を生成してください。
            なお、「{char1}」が質問して「{char2}」が回答する形で対話を行い、各発言は400文字以内とします。
            {"対話は特に制限を設けず、話題から逸れない形で可能な限り長いシナリオを作成してください。" if mode in [2, 4] else "会話は必ず4回のやりとりまでに制限してください。"}
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

def generate_scenario(url_or_file: str, char1: str, char2: str, mode: int) -> List[Tuple[str, str]]:
    if url_or_file.startswith("http"):
        print(f"Scraping content from: {url_or_file}")
        if "github.com" in url_or_file:
            content = extract_github_readme(url_or_file)
        else:
            content = scrape_website(url_or_file)
        dialogue = generate_dialogue(content, char1, char2, mode)
    else:
        print(f"Loading dialogue from file: {url_or_file}")
        dialogue = load_dialogue(url_or_file)

    dialogue = [(speaker, text) for speaker, text in dialogue]

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
        print("使用方法: python script.py <URL or file> [character1] [character2] [mode]")
        sys.exit(1)

    url_or_file = sys.argv[1]
    char1 = sys.argv[2] if len(sys.argv) > 2 else "ずんだもん"
    char2 = sys.argv[3] if len(sys.argv) > 3 else "四国めたん"
    mode = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    if char1 not in characters or char2 not in characters:
        print("指定されたキャラクターが存在しません。")
        sys.exit(1)

    dialogue = generate_scenario(url_or_file, char1, char2, mode)
