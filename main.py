import os
import sys
import requests
from bs4 import BeautifulSoup
from typing import List, Tuple
from generate_voice import generate_voice
from add_subtitles import create_video_with_subtitles
from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoFileClip
import google.generativeai as genai

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
)

def scrape_website(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text()

    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text

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

            これらの設定と使用する話題に基づいて、話題から大きく外れないように自然で面白い対話を生成してください。
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

def create_dialogue_audio(dialogue: List[Tuple[int, str]], output_dir: str) -> List[str]:
    audio_files = []
    for i, (speaker, text) in enumerate(dialogue):
        audio_file = os.path.join(output_dir, f"audio_{i}.wav")
        if speaker == 1: 
            generate_voice(text, speaker=3, output_file=audio_file, speed_scale=1.4)
        else:  
            generate_voice(text, speaker=2, output_file=audio_file, speed_scale=1.3)
        audio_files.append(audio_file)
    return audio_files

def create_dialogue_video(dialogue: List[Tuple[int, str]], audio_files: List[str], output_dir: str) -> List[str]:
    video_files = []
    for i, ((speaker, text), audio_file) in enumerate(zip(dialogue, audio_files)):
        audio_duration = AudioFileClip(audio_file).duration
        video_file = os.path.join(output_dir, f"video_{i}.mp4")
        character = "四国めたん" if speaker == 0 else "ずんだもん"
        create_video_with_subtitles(text, character, duration=audio_duration, output_file=video_file, 
                                    font_path=None)
        video_files.append(video_file)
    return video_files

def combine_dialogue_clips(video_files: List[str], audio_files: List[str], output_file: str):
    clips = [VideoFileClip(video).set_audio(AudioFileClip(audio)) 
             for video, audio in zip(video_files, audio_files)]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac")

def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"Scraping content from: {url}")
        content = scrape_website(url)
    else:
        print("No URL provided. Using default dialogue generation.")
        content = ""

    output_dir = "tmp"
    os.makedirs(output_dir, exist_ok=True)

    dialogue = generate_dialogue(content)
    print("生成された対話:")
    for speaker, text in dialogue:
        character_name = "四国めたん" if speaker == 0 else "ずんだもん"
        print(f"{character_name}: {text}")

    audio_files = create_dialogue_audio(dialogue, output_dir)
    video_files = create_dialogue_video(dialogue, audio_files, output_dir)

    final_output = "final_dialogue_output.mp4"
    combine_dialogue_clips(video_files, audio_files, final_output)

    for file in audio_files + video_files:
        os.remove(file)
    os.rmdir(output_dir)

    print(f"対話動画が完成しました: {final_output}")

if __name__ == "__main__":
    main()
