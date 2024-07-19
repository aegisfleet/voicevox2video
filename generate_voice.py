import requests
import json
import os

def generate_voice(text, speaker=1, output_file="output.wav"):
    # VOICEVOXサーバーのURL
    # 環境変数「VOICEVOX_API_HOST」の値を使用する
    voicevox_api_host = os.getenv('VOICEVOX_API_HOST', 'localhost')
    if not voicevox_api_host:
        raise ValueError("VOICEVOX_API_HOST environment variable is not set.")
    base_url = f"http://{voicevox_api_host}:50021"

    # 音声合成用のクエリを作成
    query_payload = {"text": text, "speaker": speaker}
    query_response = requests.post(f"{base_url}/audio_query", params=query_payload)
    query_response.raise_for_status()
    query_data = query_response.json()

    # 音声合成を実行
    synthesis_payload = {"speaker": speaker}
    synthesis_response = requests.post(
        f"{base_url}/synthesis",
        headers={"Content-Type": "application/json"},
        params=synthesis_payload,
        data=json.dumps(query_data)
    )
    synthesis_response.raise_for_status()

    # 音声ファイルを保存
    with open(output_file, "wb") as f:
        f.write(synthesis_response.content)

    print(f"音声ファイルが生成されました: {output_file}")

if __name__ == "__main__":
    text = "こんにちは、VOICEVOXの音声です。"
    generate_voice(text)
