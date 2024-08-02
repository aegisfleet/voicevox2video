import os
import json
import google.generativeai as genai
import argparse
import random
from content_loader import ContentLoader
from typing import List, Tuple

CONFIG_DIR = 'config'
OUTPUT_DIR = 'output'
API_KEY_FILE = '.gemini_api_key'
DIALOGUE_OUTPUT_FILE = 'generated_dialogue.txt'

def load_json_config(filename: str) -> dict:
    config_path = os.path.join(CONFIG_DIR, filename)
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

class DialogueGenerator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    @staticmethod
    def get_character_interaction(char1: str, char2: str) -> Tuple[str, str]:
        return character_interactions.get(f"{char1},{char2}", (char2, char2))

    @staticmethod
    def correct_spelling(text: str) -> str:
        for misspelling, correction in spelling_corrections.items():
            text = text.replace(misspelling, correction)
        return text

    def generate_dialogue(self, content: str, char1: str, char2: str, mode: int) -> List[Tuple[str, str]]:
        char1_call, char2_call = self.get_character_interaction(char1, char2)

        prompt = f"""
キャラクターの設定と会話に使用する話題に基づいて、{"話題に対する深い考察を行いながら自然で面白い" if mode in [1, 2] else "話題の内容を正確に説明するための"}対話を生成してください。
なお、「{char1}」が質問して「{char2}」が回答する形で対話を行い、感情表現に絵文字を多数使用して各発言は400文字以内とします。
{"対話は特に制限を設けず、話題から逸れない形で可能な限り長いシナリオを作成してください。" if mode in [2, 4] else "会話は必ず4回のやりとりまでに制限してください。"}

対話の出力形式は以下のように1行目にタイトル、2行目に対話の雰囲気、3行目以降に対話内容を記載してください：
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
{content[:10000]}
        """
        print(prompt)

        for retry in range(3):
            try:
                response = self.model.start_chat().send_message(prompt)
                dialogue = []
                for line in response.text.strip().split('\n'):
                    if ':' in line:
                        speaker, text = line.split(':', 1)
                        speaker = speaker.replace("## タイトル", "タイトル").replace("##  タイトル", "タイトル")
                        dialogue.append((speaker.strip(), self.correct_spelling(text.strip())))
                return dialogue
            except ValueError as e:
                print(f"エラーが発生しました: {e}")
                print(f"リトライ {retry+1} 回目...")
        return []

class FileHandler:
    @staticmethod
    def save_dialogue(dialogue: List[Tuple[str, str]]) -> None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        dialogue_file = os.path.join(OUTPUT_DIR, DIALOGUE_OUTPUT_FILE)
        with open(dialogue_file, 'w', encoding='utf-8') as f:
            for speaker, text in dialogue:
                f.write(f"{speaker}: {text}\n")
        print(f"\n対話が保存されました: {dialogue_file}")

class ScenarioGenerator:
    def __init__(self):
        self.api_key = APIKeyManager.get_api_key()
        self.dialogue_generator = DialogueGenerator(self.api_key)

    def generate_scenario(self, url_or_file: str, char1: str, char2: str, mode: int) -> List[Tuple[str, str]]:
        content = ContentLoader.load_content(url_or_file)

        dialogue = self.dialogue_generator.generate_dialogue(content, char1, char2, mode)

        print("\n生成された対話:")
        for speaker, text in dialogue:
            print(f"{speaker}: {text}")

        FileHandler.save_dialogue(dialogue)

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

    scenario_generator = ScenarioGenerator()
    scenario_generator.generate_scenario(args.url_or_file, args.char1, args.char2, args.mode)

if __name__ == "__main__":
    main()
