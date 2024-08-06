import os

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

class GeminiHandler:
    model = None

    @classmethod
    def initialize(cls, api_key: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        cls.model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    @classmethod
    def generate_content(cls, prompt: str) -> str:
        if not cls.model:
            raise RuntimeError("GeminiHandler が初期化されていません。まず GeminiHandler.initialize(api_key) を呼び出してください。")
        response = cls.model.generate_content(prompt)
        return response.text.strip() if response.text else "コンテンツの生成に失敗しました。"
