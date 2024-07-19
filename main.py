import os
from typing import List, Tuple
from generate_voice import generate_voice
from add_subtitles import create_video_with_subtitles
from combine_audio_video import combine_audio_video
from moviepy.editor import AudioFileClip, concatenate_videoclips
import google.generativeai as genai

# Gemini API の設定
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
)

def generate_dialogue() -> List[Tuple[int, str]]:
    chat_session = model.start_chat(history=[])

    prompt = """
    2人のキャラクターによる短い対話を生成してください。各発言は200文字以内で、合計4つの発言にしてください。
    対話の形式は以下のようにしてください：
    0: [四国めたんの発言]
    1: [ずんだもんの発言]
    0: [四国めたんの発言]
    1: [ずんだもんの発言]

    キャラクター設定：

    四国めたん（キャラクター0）:
    - 高等部二年生の女の子。第一人称はわたくし
    - 常に金欠。趣味は中二病妄想
    - 誰にでも遠慮せず、若干ツンデレ気味
    - 口調：基本的にタメ口
    - 相手のことを「ずんだもん」と呼ぶ
    - 色々なことを知っている

    ずんだもん（キャラクター1）:
    - ずんだ餅の精。第一人称はボクまたはずんだもん
    - やや不幸属性が備わっており、ないがしろにされることもしばしば
    - 趣味はその辺をふらふらすること、自分を大きく見せること
    - 口調：不自然な日本語にならない限り、語尾に必ず「～のだ」「～なのだ」をつけて喋る
    - 相手のことを「めたん」と呼ぶ
    - あまり知識がないが好奇心旺盛

    これらの設定に基づいて、自然で面白い対話を生成してください。
    """

    response = chat_session.send_message(prompt)

    dialogue = []
    for line in response.text.strip().split('\n'):
        speaker, text = line.split(':', 1)
        dialogue.append((int(speaker), text.strip()))

    return dialogue

def create_dialogue_audio(dialogue: List[Tuple[int, str]], output_dir: str) -> List[str]:
    audio_files = []
    for i, (speaker, text) in enumerate(dialogue):
        audio_file = os.path.join(output_dir, f"audio_{i}.wav")
        generate_voice(text, speaker=speaker, output_file=audio_file)
        audio_files.append(audio_file)
    return audio_files

def create_dialogue_video(dialogue: List[Tuple[int, str]], audio_files: List[str], output_dir: str) -> List[str]:
    video_files = []
    for i, ((speaker, text), audio_file) in enumerate(zip(dialogue, audio_files)):
        audio_duration = AudioFileClip(audio_file).duration
        video_file = os.path.join(output_dir, f"video_{i}.mp4")
        create_video_with_subtitles(text, duration=audio_duration, output_file=video_file, 
                                    position='bottom' if speaker == 0 else 'top',
                                    font_path=None)
        video_files.append(video_file)
    return video_files

def combine_dialogue_clips(video_files: List[str], audio_files: List[str], output_file: str):
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    clips = [VideoFileClip(video).set_audio(AudioFileClip(audio)) 
             for video, audio in zip(video_files, audio_files)]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(output_file)

def main():
    output_dir = "tmp"
    os.makedirs(output_dir, exist_ok=True)

    # Gemini APIを使用して対話を生成
    dialogue = generate_dialogue()
    print("生成された対話:")
    for speaker, text in dialogue:
        character_name = "四国めたん" if speaker == 0 else "ずんだもん"
        print(f"{character_name}: {text}")

    audio_files = create_dialogue_audio(dialogue, output_dir)
    video_files = create_dialogue_video(dialogue, audio_files, output_dir)

    final_output = "final_dialogue_output.mp4"
    combine_dialogue_clips(video_files, audio_files, final_output)

    # Clean up temporary files
    for file in audio_files + video_files:
        os.remove(file)
    os.rmdir(output_dir)

    print(f"対話動画が完成しました: {final_output}")

if __name__ == "__main__":
    main()
