import requests
import json
import os
from pydub import AudioSegment
from typing import Union, Dict, Any

CHARACTERS_JSON = "./config/characters.json"

def generate_voice(text: str, character_name: str, output_file: str = "output.wav") -> None:
    voicevox_api_host = os.getenv('VOICEVOX_API_HOST', 'localhost')
    if not voicevox_api_host:
        raise ValueError("VOICEVOX_API_HOST environment variable is not set.")
    base_url = f"http://{voicevox_api_host}:50021"

    text = text.replace("。", "。 ").replace("、", "、 ")

    character_config = load_character_config(character_name)

    query_payload = {"text": text, "speaker": character_config["speaker_id"]}
    query_data = send_request(f"{base_url}/audio_query", method="POST", params=query_payload)

    if isinstance(query_data, dict):
        query_data.update({
            "speedScale": character_config["speed_scale"],
            "volumeScale": character_config["volume_scale"],
            "intonationScale": character_config["intonation_scale"],
            "prePhonemeLength": character_config["pre_phoneme_length"],
            "postPhonemeLength": character_config["post_phoneme_length"],
            "emphasisScale": character_config["emphasis_scale"],
            "breathScale": character_config["breath_scale"]
        })

        synthesis_payload = {"speaker": character_config["speaker_id"]}
        audio_data = send_request(
            f"{base_url}/synthesis",
            method="POST",
            params=synthesis_payload,
            data=json.dumps(query_data),
            headers={"Content-Type": "application/json"}
        )

        if isinstance(audio_data, bytes):
            save_audio(audio_data, output_file)
            print(f"音声ファイルが生成されました: {output_file}")
        else:
            print("音声データの取得に失敗しました。")
    else:
        print("音声クエリの作成に失敗しました。")

def send_request(url: str, method: str = "GET", **kwargs) -> Union[Dict[str, Any], bytes]:
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json() if response.headers.get('content-type') == 'application/json' else response.content
    except requests.exceptions.ConnectionError:
        raise SystemExit("エラー: VOICEVOXのDockerコンテナが起動しているか確認してください。")
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"エラー: リクエスト中に問題が発生しました: {e}")

def save_audio(audio_data: bytes, output_file: str) -> None:
    temp_file = "temp_output.wav"
    with open(temp_file, "wb") as f:
        f.write(audio_data)

    sound = AudioSegment.from_wav(temp_file)
    silence = AudioSegment.silent(duration=300)
    (sound + silence).export(output_file, format="wav")

    os.remove(temp_file)

def load_character_config(character_name: str) -> Dict[str, Any]:
    with open(CHARACTERS_JSON, "r", encoding="utf-8") as f:
        characters = json.load(f)

    if character_name not in characters:
        raise ValueError(f"キャラクター '{character_name}' は設定ファイルに見つかりません。")

    return characters[character_name]

if __name__ == "__main__":
    generate_voice("こんにちは、VOICEVOXの音声です。", "ずんだもん", "tmp/zundamon_greeting.wav")
    generate_voice("四国めたんの声をお届けします。", "四国めたん", "tmp/shikokumetan_voice.wav")
    generate_voice("春日部つむぎだYO！", "春日部つむぎ", "tmp/tsumugi_voice.wav")
