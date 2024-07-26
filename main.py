import argparse
import os
import shutil
import json
import base64
import tempfile
from typing import List, Tuple, Dict
from generate_voice import generate_voice
from generate_movie import create_video_with_subtitles
from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeAudioClip, ColorClip
import wave
import numpy as np
from scipy import signal
from generate_scenario import generate_scenario

CONFIG_PATH = 'config/characters.json'
OUTPUT_DIR = 'tmp'
FINAL_OUTPUT = 'output/final_dialogue_output.mp4'
BGM_FILE = './bgm/のんきな日常.bin'

def load_character_config() -> Dict:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

CHARACTER_CONFIG = load_character_config()

def create_audio_file(character: str, text: str, output_file: str) -> None:
    char_config = CHARACTER_CONFIG[character]
    generate_voice(text, speaker=char_config['speaker_id'], output_file=output_file, 
                   speed_scale=char_config.get('speed_scale', 1.0),
                   volume_scale=char_config.get('volume_scale', 1.0),
                   intonation_scale=char_config.get('intonation_scale', 1.0))

    process_audio_file(output_file)

def process_audio_file(file_path: str) -> None:
    with wave.open(file_path, 'rb') as wf:
        params = wf.getparams()
        data = wf.readframes(wf.getnframes())

    data = remove_noise(data, params.framerate)

    with wave.open(file_path, 'wb') as wf:
        wf.setparams(params)
        wf.writeframes(data)

def remove_noise(audio_data: bytes, sample_rate: int, cutoff: int = 100, threshold: float = 0.01, 
                 fade_duration_ms: int = 10, limit_threshold: float = 0.8) -> bytes:
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

    audio_array = np.clip(audio_array / np.max(np.abs(audio_array)) * limit_threshold, -1, 1)
    return (audio_array * 32767.0).astype(np.int16).tobytes()

def create_dialogue_files(dialogue: List[Tuple[str, str]], is_vertical: bool, title: str) -> Tuple[List[str], List[str]]:
    audio_files = []
    video_files = []
    animation_types = ["slide_bottom", "fade", "slide_right", "slide_left", "slide_top"]

    for i, (character, text) in enumerate(dialogue, start=1):
        audio_file = os.path.join(OUTPUT_DIR, f"audio_{i}.wav")
        video_file = os.path.join(OUTPUT_DIR, f"video_{i}.mp4")

        create_audio_file(character, text, audio_file)
        audio_duration = AudioFileClip(audio_file).duration

        create_video_with_subtitles(text, character, duration=audio_duration, output_file=video_file, 
                                    font_path=None, animation_type=animation_types[i % len(animation_types)], 
                                    is_vertical=is_vertical, title=title)

        audio_files.append(audio_file)
        video_files.append(video_file)

    return audio_files, video_files

def decode_bgm(bgm_file: str) -> str:
    with open(bgm_file, "rb") as f:
        encoded_data = f.read()

    decoded_data = base64.b64decode(encoded_data)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.write(decoded_data)
    temp_file.close()

    return temp_file.name

def combine_dialogue_clips(video_files: List[str], audio_files: List[str], output_file: str, bgm_file: str, is_vertical: bool) -> None:
    clips = [VideoFileClip(video).set_audio(AudioFileClip(audio)) for video, audio in zip(video_files, audio_files)]

    for i, clip in enumerate(clips):
        clip = clip.audio_fadein(0.1).audio_fadeout(0.3)
        if i == 0:
            clip = clip.fadein(0.5)
        if i == len(clips) - 1:
            clip = clip.fadeout(0.5)
        clips[i] = clip

    size = (720, 1280) if is_vertical else (1280, 720)
    blank_clip = ColorClip(size=size, color=(0, 0, 0)).set_duration(1)
    final_clip = concatenate_videoclips([blank_clip] + clips + [blank_clip], method="compose")

    tmp_bgm_file = decode_bgm(bgm_file)
    bgm = AudioFileClip(tmp_bgm_file).volumex(0.1)
    bgm = bgm.audio_loop(duration=final_clip.duration) if bgm.duration < final_clip.duration else bgm.subclip(0, final_clip.duration)
    bgm = bgm.audio_fadein(1).audio_fadeout(3)

    final_audio = CompositeAudioClip([final_clip.audio, bgm])
    final_clip = final_clip.set_audio(final_audio)

    temp_audiofile = os.path.join(OUTPUT_DIR, "final_dialogue_outputTEMP_MPY_wvf_snd.mp4")
    final_clip.write_videofile(output_file, codec="libx264", audio_codec="aac", bitrate="5000k", audio_bitrate="192k", temp_audiofile=temp_audiofile)

    os.unlink(tmp_bgm_file)

def clean_output_directory(directory: str) -> None:
    if os.path.exists(directory):
        for item in os.listdir(directory):
            if not item.startswith('.'):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
    else:
        os.makedirs(directory)

def log_parameters(args):
    print(f"使用するパラメータ:\nURL/ファイル: {args.url_or_file}\nキャラクター1: {args.char1}\nキャラクター2: {args.char2}")
    print(f"長い対話: {'はい' if args.mode in [2, 4] else 'いいえ'}\n縦型動画: {'はい' if args.vertical else 'いいえ'}")

def main() -> None:
    parser = argparse.ArgumentParser(description="対話動画生成スクリプト")
    parser.add_argument("url_or_file", help="URLまたはファイルパス")
    parser.add_argument("-c1", "--char1", default="ずんだもん", help="キャラクター1 (デフォルト: ずんだもん)")
    parser.add_argument("-c2", "--char2", default="四国めたん", help="キャラクター2 (デフォルト: 四国めたん)")
    parser.add_argument("-m", "--mode", type=int, choices=[1, 2, 3, 4], default=1, help="対話モード (デフォルト: 1)")
    parser.add_argument("-v", "--vertical", action="store_true", help="縦型動画を生成")

    args = parser.parse_args()

    if args.char1 not in CHARACTER_CONFIG or args.char2 not in CHARACTER_CONFIG:
        print("指定されたキャラクターが存在しません。デフォルトのキャラクターを使用します。")
        args.char1, args.char2 = "ずんだもん", "四国めたん"

    if args.url_or_file.endswith('.txt'):
        with open(args.url_or_file, 'r', encoding='utf-8') as f:
            content = f.read().strip().split('\n')

        print("テキストファイルの内容:")
        for line in content:
            print(line)

        if content[0].startswith("タイトル:"):
            title = content[0].split(":")[1].strip()
            dialogue = [(line.split(":")[0], line.split(":")[1]) for line in content[1:]]
        else:
            title = ""
            try:
                dialogue = [(line.split(":")[0], line.split(":")[1]) for line in content]
            except IndexError:
                print("シナリオを生成します。")
                log_parameters(args)
                scenario = generate_scenario(args.url_or_file, args.char1, args.char2, args.mode)
                title = scenario[0][1].strip() if scenario and scenario[0][0] == "タイトル" else ""
                dialogue = scenario[1:] if title else scenario
    else:
        log_parameters(args)
        scenario = generate_scenario(args.url_or_file, args.char1, args.char2, args.mode)
        title = scenario[0][1].strip() if scenario and scenario[0][0] == "タイトル" else ""
        dialogue = scenario[1:] if title else scenario

    clean_output_directory(OUTPUT_DIR)

    audio_files, video_files = create_dialogue_files(dialogue, args.vertical, title)
    combine_dialogue_clips(video_files, audio_files, FINAL_OUTPUT, BGM_FILE, args.vertical)

    print(f"対話動画が完成しました: {FINAL_OUTPUT}")

if __name__ == "__main__":
    main()
