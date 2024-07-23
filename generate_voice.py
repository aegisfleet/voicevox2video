import requests
import json
import os
from pydub import AudioSegment

def generate_voice(text, speaker=3, output_file="output.wav", speed_scale=1.3, volume_scale=3.5, intonation_scale=1.0):
    voicevox_api_host = os.getenv('VOICEVOX_API_HOST', 'localhost')
    if not voicevox_api_host:
        raise ValueError("VOICEVOX_API_HOST environment variable is not set.")
    base_url = f"http://{voicevox_api_host}:50021"

    text = text.replace("。", "。 ").replace("、", "、 ")

    query_payload = {"text": text, "speaker": speaker}
    try:
        query_response = requests.post(f"{base_url}/audio_query", params=query_payload)
        query_response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise SystemExit("エラー: VOICEVOXのDockerコンテナが起動しているか確認してください。")
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"エラー: リクエスト中に問題が発生しました: {e}")

    query_data = query_response.json()

    query_data["speedScale"] = speed_scale
    query_data["volumeScale"] = volume_scale
    query_data["intonationScale"] = intonation_scale

    synthesis_payload = {"speaker": speaker}
    try:
        synthesis_response = requests.post(
            f"{base_url}/synthesis",
            headers={"Content-Type": "application/json"},
            params=synthesis_payload,
            data=json.dumps(query_data)
        )
        synthesis_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"エラー: 音声合成リクエストで問題が発生しました: {e}")

    temp_output_file = "temp_output.wav"
    with open(temp_output_file, "wb") as f:
        f.write(synthesis_response.content)

    sound = AudioSegment.from_wav(temp_output_file)
    silence = AudioSegment.silent(duration=300)
    combined = sound + silence
    combined.export(output_file, format="wav")

    os.remove(temp_output_file)

    print(f"音声ファイルが生成されました: {output_file}")

if __name__ == "__main__":
    text = "こんにちは、VOICEVOXの音声です。"
    generate_voice(text)
