import os
from typing import List, Tuple
from generate_voice import generate_voice
from add_subtitles import create_video_with_subtitles
from combine_audio_video import combine_audio_video
from moviepy.editor import AudioFileClip, concatenate_videoclips

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
    dialogue = [
        (0, "こんにちは、私は1人目のキャラクターです。"),
        (1, "こんにちは、私は2人目のキャラクターです。"),
        (0, "今日はいい天気ですね。"),
        (1, "そうですね。散歩でもいきましょうか？"),
    ]

    output_dir = "tmp"
    os.makedirs(output_dir, exist_ok=True)

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
