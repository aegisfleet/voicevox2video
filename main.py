import os
import shutil
import sys
from typing import List, Tuple
from generate_voice import generate_voice
from generate_movie import create_video_with_subtitles
from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeAudioClip, ColorClip
import wave
import numpy as np
from scipy import signal
from generate_scenario import generate_scenario

CHARACTER_TO_SPEAKER = {
    "四国めたん": 2,
    "ずんだもん": 3,
    "春日部つむぎ": 8,
    "雨晴はう": 10,
    "波音リツ": 9,
    "玄野武宏": 11,
    "白上虎太郎": 12,
    "青山龍星": 13,
    "冥鳴ひまり": 14,
    "もち子さん": 20,
    "剣崎雌雄": 21
}

def create_audio_file(character: str, text: str, output_file: str):
    speaker = CHARACTER_TO_SPEAKER.get(character, 2)
    speed_scale = 1.4 if character == "ずんだもん" else 1.3
    generate_voice(text, speaker=speaker, output_file=output_file, speed_scale=speed_scale)

    with wave.open(output_file, 'rb') as wf:
        params = wf.getparams()
        data = wf.readframes(wf.getnframes())

    data = remove_noise(data, params.framerate, cutoff=100, fade_duration_ms=10, limit_threshold=0.8)

    with wave.open(output_file, 'wb') as wf:
        wf.setparams(params)
        wf.writeframes(data)

def create_dialogue_audio(dialogue: List[Tuple[str, str]], output_dir: str) -> List[str]:
    audio_files = []
    for i, (character, text) in enumerate(dialogue):
        audio_file = os.path.join(output_dir, f"audio_{i}.wav")
        create_audio_file(character, text, audio_file)
        audio_files.append(audio_file)
    return audio_files

def limit_audio(audio_array, threshold=0.8):
    max_val = np.max(np.abs(audio_array))
    if (max_val > threshold):
        audio_array = audio_array / max_val * threshold
    return audio_array

def remove_noise(audio_data, sample_rate, cutoff=100, threshold=0.01, fade_duration_ms=10, limit_threshold=0.8):
    audio_array = np.frombuffer(audio_data, dtype=np.int16) / 32768.0
    nyquist = 0.5 * sample_rate
    normal_cutoff = cutoff / nyquist
    b, a = signal.butter(4, normal_cutoff, btype='high', analog=False)
    audio_array = signal.filtfilt(b, a, audio_array)
    audio_array = np.where(np.abs(audio_array) > threshold, audio_array, audio_array * 0.1)
    fade_duration = int(fade_duration_ms * sample_rate / 1000)
    fade_in = np.linspace(0, 1, fade_duration)
    fade_out = np.linspace(1, 0, fade_duration)
    audio_array[:fade_duration] *= fade_in
    audio_array[-fade_duration:] *= fade_out
    audio_array = limit_audio(audio_array, threshold=limit_threshold)
    audio_array = np.clip(audio_array, -1, 1)
    audio_array = (audio_array * 32767.0).astype(np.int16)
    return audio_array.tobytes()

def create_video_file(character: str, text: str, audio_file: str, output_file: str, is_vertical: bool, animation_type: str):
    audio_duration = AudioFileClip(audio_file).duration
    create_video_with_subtitles(text, character, duration=audio_duration, output_file=output_file, 
                                font_path=None, animation_type=animation_type, is_vertical=is_vertical)

def create_dialogue_video(dialogue: List[Tuple[str, str]], audio_files: List[str], output_dir: str, is_vertical: bool) -> List[str]:
    video_files = []
    animation_types = ["fade", "slide_right", "slide_left", "slide_top", "slide_bottom"]
    for i, ((character, text), audio_file) in enumerate(zip(dialogue, audio_files)):
        video_file = os.path.join(output_dir, f"video_{i}.mp4")
        animation_type = animation_types[i % len(animation_types)]
        create_video_file(character, text, audio_file, video_file, is_vertical, animation_type)
        video_files.append(video_file)
    return video_files

def combine_dialogue_clips(video_files: List[str], audio_files: List[str], output_file: str, bgm_file: str, is_vertical: bool):
    clips = [VideoFileClip(video).set_audio(AudioFileClip(audio)) for video, audio in zip(video_files, audio_files)]
    crossfaded_clips = []
    fade_in_duration = 0.1
    fade_out_duration = 0.3
    blank_duration = 1
    size = (720, 1280) if is_vertical else (1280, 720)
    blank_clip = ColorClip(size=size, color=(0, 0, 0)).set_duration(blank_duration)
    for i, clip in enumerate(clips):
        if i > 0:
            clip = clip.crossfadein(fade_in_duration)
        if i < len(clips) - 1:
            clip = clip.crossfadeout(fade_out_duration)
        clip = clip.audio_fadein(fade_in_duration).audio_fadeout(fade_out_duration)
        crossfaded_clips.append(clip)
    final_clip = concatenate_videoclips([blank_clip] + crossfaded_clips + [blank_clip], method="compose")
    bgm = AudioFileClip(bgm_file).volumex(0.1)
    bgm = bgm.audio_loop(duration=final_clip.duration) if bgm.duration < final_clip.duration else bgm.subclip(0, final_clip.duration)
    bgm = bgm.audio_fadein(1).audio_fadeout(3)
    final_audio = CompositeAudioClip([final_clip.audio, bgm])
    final_clip = final_clip.set_audio(final_audio)
    final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac", bitrate="5000k", audio_bitrate="192k")

def main():
    if len(sys.argv) > 1:
        url_or_file = sys.argv[1]
        dialogue = generate_scenario(url_or_file)
    else:
        print("No URL or file provided. Using default dialogue generation.")
        dialogue = generate_scenario("")
    is_vertical = len(sys.argv) > 2 and sys.argv[2] == "1"
    output_dir = "tmp"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    audio_files = create_dialogue_audio(dialogue, output_dir)
    video_files = create_dialogue_video(dialogue, audio_files, output_dir, is_vertical)
    final_output = "output/final_dialogue_output.mp4"
    bgm_file = "./bgm/のんきな日常.mp3"
    combine_dialogue_clips(video_files, audio_files, final_output, bgm_file, is_vertical)
    for file in audio_files + video_files:
        os.remove(file)
    os.rmdir(output_dir)
    print(f"対話動画が完成しました: {final_output}")

if __name__ == "__main__":
    main()
