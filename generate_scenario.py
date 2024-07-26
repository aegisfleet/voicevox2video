import os
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple
import google.generativeai as genai
import argparse
import random
import chardet

def load_json_config(filename: str) -> dict:
    config_path = os.path.join('config', filename)
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

characters = load_json_config('characters.json')
character_interactions = load_json_config('character_interactions.json')

spelling_corrections = {
    "## タイトル:": "タイトル:",
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
            text_node.replace_with(text_node.replace(phrase, ""))

    main_content = [tag.get_text(strip=True) for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']) if tag.get_text(strip=True)]
    return "\n".join(main_content)

def extract_github_readme(url: str) -> str:
    readme_url = f"{url.rstrip('/')}/raw/main/README.md"
    response = requests.get(readme_url)
    if response.status_code != 200:
        readme_url = f"{url.rstrip('/')}/raw/master/README.md"
        response = requests.get(readme_url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        lines = [line.strip() for line in soup.get_text().split('\n')]
        return '\n'.join(line for line in lines if line and not line.startswith('```'))
    return ""

def get_character_interaction(char1: str, char2: str) -> Tuple[str, str]:
    return character_interactions.get(f"{char1},{char2}", (char2, char2))

def correct_spelling(text: str) -> str:
    for misspelling, correction in spelling_corrections.items():
        text = text.replace(misspelling, correction)
    return text

def generate_dialogue(content: str, char1: str, char2: str, mode: int) -> List[Tuple[str, str]]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("エラー: GEMINI_API_KEY環境変数が設定されていません。")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    char1_call, char2_call = get_character_interaction(char1, char2)

    prompt = f"""
キャラクターの設定と会話に使用する話題に基づいて、{"話題に対する深い考察を行いながら自然で面白い" if mode in [1, 2] else "話題の内容を正確に説明するための"}対話を生成してください。
なお、「{char1}」が質問して「{char2}」が回答する形で対話を行い、各発言は400文字以内とします。
{"対話は特に制限を設けず、話題から逸れない形で可能な限り長いシナリオを作成してください。" if mode in [2, 4] else "会話は必ず4回のやりとりまでに制限してください。"}

対話の出力形式は以下のように1行目にタイトルを記載し、2行目以降に対話内容を記載してください：
...
タイトル: [話題の内容を取り入れた視聴者の興味を引くタイトル]
雰囲気: [対話の雰囲気を端的な形容詞で記載]
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
    """

    for retry in range(3):
        try:
            response = model.start_chat().send_message(prompt)
            dialogue = []
            for line in response.text.strip().split('\n'):
                if ':' in line:
                    speaker, text = line.split(':', 1)
                    dialogue.append((speaker.strip(), correct_spelling(text.strip())))
            return dialogue
        except ValueError as e:
            print(f"エラーが発生しました: {e}")
            print(f"リトライ {retry+1} 回目...")
    return []

def read_file_with_encoding(file_path: str) -> str:
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    encoding = chardet.detect(raw_data)['encoding']
    try:
        return raw_data.decode(encoding)
    except UnicodeDecodeError:
        print(f"警告: {encoding}でのデコードに失敗しました。UTF-8で再試行します。")
        return raw_data.decode('utf-8')

def generate_scenario(url_or_file: str, char1: str, char2: str, mode: int) -> List[Tuple[str, str]]:
    if url_or_file.startswith("http"):
        print(f"Scraping content from: {url_or_file}")
        content = extract_github_readme(url_or_file) if "github.com" in url_or_file else scrape_website(url_or_file)
    else:
        print(f"Loading content from file: {url_or_file}")
        content = read_file_with_encoding(url_or_file)

    dialogue = generate_dialogue(content, char1, char2, mode)

    print("\n生成された対話:")
    for speaker, text in dialogue:
        print(f"{speaker}: {text}")

    dialogue_file = "output/generated_dialogue.txt"
    with open(dialogue_file, 'w', encoding='utf-8') as f:
        for speaker, text in dialogue:
            f.write(f"{speaker}: {text}\n")
    print(f"\n対話が保存されました: {dialogue_file}")

    return dialogue

def main():
    parser = argparse.ArgumentParser(description="対話シナリオ生成スクリプト")
    parser.add_argument("url_or_file", help="URLまたはファイルパス")
    parser.add_argument("-c1", "--char1", help="キャラクター1")
    parser.add_argument("-c2", "--char2", help="キャラクター2")
    parser.add_argument("-m", "--mode", type=int, choices=[1, 2, 3, 4], default=1, help="対話モード (デフォルト: 1)")

    args = parser.parse_args()

    available_characters = list(characters.keys())
    if not args.char1:
        args.char1 = random.choice(available_characters)
    if not args.char2:
        args.char2 = random.choice([char for char in available_characters if char != args.char1])

    if args.char1 not in characters or args.char2 not in characters:
        print("指定されたキャラクターが存在しません。")
        return

    print(f"使用するパラメータ:")
    print(f"URL/ファイル: {args.url_or_file}")
    print(f"キャラクター1: {args.char1}")
    print(f"キャラクター2: {args.char2}")
    print(f"対話モード: {args.mode}")

    generate_scenario(args.url_or_file, args.char1, args.char2, args.mode)

if __name__ == "__main__":
    main()
