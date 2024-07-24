import argparse
import os
import shutil
import json
from typing import List, Tuple
from generate_voice import generate_voice
from generate_movie import create_video_with_subtitles
from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeAudioClip, ColorClip
import wave
import numpy as np
from scipy import signal
from generate_scenario import generate_scenario

def load_character_config():
    with open('config/characters.json', 'r', encoding='utf-8') as f:
        return json.load(f)

CHARACTER_CONFIG = load_character_config()

def create_audio_file(character: str, text: str, output_file: str):
    char_config = CHARACTER_CONFIG[character]
    speaker = char_config['speaker_id']
    speed_scale = char_config.get('speed_scale', 1.0)
    volume_scale = char_config.get('volume_scale', 1.0)
    intonation_scale = char_config.get('intonation_scale', 1.0)

    generate_voice(text, speaker=speaker, output_file=output_file, 
                   speed_scale=speed_scale, volume_scale=volume_scale, 
                   intonation_scale=intonation_scale)

    with wave.open(output_file, 'rb') as wf:
        params = wf.getparams()
        data = wf.readframes(wf.getnframes())

    data = remove_noise(data, params.framerate, cutoff=100, fade_duration_ms=10, limit_threshold=0.8)

    with wave.open(output_file, 'wb') as wf:
        wf.setparams(params)
        wf.writeframes(data)

def create_dialogue_audio(dialogue: List[Tuple[str, str]], output_dir: str) -> List[str]:
    audio_files = []
    for i, (character, text) in enumerate(dialogue, start=1):
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

def create_video_file(character: str, text: str, audio_file: str, output_file: str, is_vertical: bool, animation_type: str, title: str):
    audio_duration = AudioFileClip(audio_file).duration
    create_video_with_subtitles(text, character, duration=audio_duration, output_file=output_file, 
                                font_path=None, animation_type=animation_type, is_vertical=is_vertical, title=title)

def create_dialogue_video(dialogue: List[Tuple[str, str]], audio_files: List[str], output_dir: str, is_vertical: bool, title: str) -> List[str]:
    video_files = []
    animation_types = ["slide_bottom", "fade", "slide_right", "slide_left", "slide_top"]
    for i, ((character, text), audio_file) in enumerate(zip(dialogue, audio_files), start=1):
        video_file = os.path.join(output_dir, f"video_{i}.mp4")
        animation_type = animation_types[i % len(animation_types)]
        create_video_file(character, text, audio_file, video_file, is_vertical, animation_type, title)
        video_files.append(video_file)
    return video_files

def combine_dialogue_clips(video_files: List[str], audio_files: List[str], output_file: str, bgm_file: str, is_vertical: bool):
    clips = [VideoFileClip(video).set_audio(AudioFileClip(audio)) for video, audio in zip(video_files, audio_files)]
    crossfaded_clips = []
    audio_fade_in_duration = 0.1
    audio_fade_out_duration = 0.3
    video_fade_in_duration = 0.5
    video_fade_out_duration = 0.5
    blank_duration = 1
    size = (720, 1280) if is_vertical else (1280, 720)
    blank_clip = ColorClip(size=size, color=(0, 0, 0)).set_duration(blank_duration)

    for i, clip in enumerate(clips):
        clip = clip.audio_fadein(audio_fade_in_duration).audio_fadeout(audio_fade_out_duration)
        if i == 0:
            clip = clip.fadein(video_fade_in_duration)
        if i == len(clips) - 1:
            clip = clip.fadeout(video_fade_out_duration)
        crossfaded_clips.append(clip)

    final_clip = concatenate_videoclips([blank_clip] + crossfaded_clips + [blank_clip], method="compose")
    bgm = AudioFileClip(bgm_file).volumex(0.1)
    bgm = bgm.audio_loop(duration=final_clip.duration) if bgm.duration < final_clip.duration else bgm.subclip(0, final_clip.duration)
    bgm = bgm.audio_fadein(1).audio_fadeout(3)
    final_audio = CompositeAudioClip([final_clip.audio, bgm])
    final_clip = final_clip.set_audio(final_audio)

    temp_audiofile = os.path.join("tmp", "final_dialogue_outputTEMP_MPY_wvf_snd.mp4")
    final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac", bitrate="5000k", audio_bitrate="192k", temp_audiofile=temp_audiofile)

def remove_visible_files(directory):
    for item in os.listdir(directory):
        if not item.startswith('.'):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

def main():
    parser = argparse.ArgumentParser(description="対話動画生成スクリプト")
    parser.add_argument("url_or_file", help="URLまたはファイルパス")
    parser.add_argument("-c1", "--char1", default="ずんだもん", help="キャラクター1 (デフォルト: ずんだもん)")
    parser.add_argument("-c2", "--char2", default="四国めたん", help="キャラクター2 (デフォルト: 四国めたん)")
    parser.add_argument("-m", "--mode", type=int, choices=[1, 2, 3, 4], default=1, help="対話モード (デフォルト: 1)")
    parser.add_argument("-v", "--vertical", action="store_true", help="縦型動画を生成")

    args = parser.parse_args()

    if args.char1 not in CHARACTER_CONFIG or args.char2 not in CHARACTER_CONFIG:
        print("指定されたキャラクターが存在しません。デフォルトのキャラクターを使用します。")
        args.char1 = "ずんだもん"
        args.char2 = "四国めたん"

    print(f"使用するパラメータ:")
    print(f"URL/ファイル: {args.url_or_file}")
    print(f"キャラクター1: {args.char1}")
    print(f"キャラクター2: {args.char2}")
    print(f"長い対話: {'はい' if args.mode in [2, 4] else 'いいえ'}")
    print(f"縦型動画: {'はい' if args.vertical else 'いいえ'}")

    scenario = generate_scenario(args.url_or_file, args.char1, args.char2, args.mode)

    if scenario and scenario[0][0] == "タイトル":
        title = scenario[0][1].strip()
        dialogue = scenario[1:]
    else:
        title = ""
        dialogue = scenario

    output_dir = "tmp"
    if os.path.exists(output_dir):
        remove_visible_files(output_dir)
    else:
        os.makedirs(output_dir)

    audio_files = create_dialogue_audio(dialogue, output_dir)
    video_files = create_dialogue_video(dialogue, audio_files, output_dir, args.vertical, title)
    final_output = "output/final_dialogue_output.mp4"
    bgm_file = "./bgm/のんきな日常.mp3"
    combine_dialogue_clips(video_files, audio_files, final_output, bgm_file, args.vertical)

    print(f"対話動画が完成しました: {final_output}")

if __name__ == "__main__":
    main()
