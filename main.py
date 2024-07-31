import argparse
import os
import shutil
import json
import base64
import tempfile
from typing import List, Tuple, Dict, Optional
from pathlib import Path

import wave
import numpy as np
from scipy import signal
from moviepy.editor import AudioFileClip, concatenate_videoclips, VideoFileClip, CompositeAudioClip, ColorClip

from generate_voice import generate_voice
from generate_movie import create_video_with_subtitles
from generate_scenario import ScenarioGenerator

CONFIG_PATH = Path('config/characters.json')
OUTPUT_DIR = Path('tmp')
FINAL_OUTPUT = Path('output/final_dialogue_output.mp4')
BGM_DIR = Path('./bgm/')

def load_character_config() -> Dict:
    with CONFIG_PATH.open('r', encoding='utf-8') as f:
        return json.load(f)

CHARACTER_CONFIG = load_character_config()

def create_audio_file(character: str, text: str, output_file: Path) -> None:
    generate_voice(text, character_name=character, output_file=str(output_file))
    process_audio_file(output_file)

def process_audio_file(file_path: Path) -> None:
    with wave.open(str(file_path), 'rb') as wf:
        params = wf.getparams()
        data = wf.readframes(wf.getnframes())

    processed_data = remove_noise(data, params.framerate)

    with wave.open(str(file_path), 'wb') as wf:
        wf.setparams(params)
        wf.writeframes(processed_data)

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

def create_dialogue_files(dialogue: List[Tuple[str, str]], is_vertical: bool, title: str) -> Tuple[List[Path], List[Path]]:
    audio_files = []
    video_files = []
    animation_types = ["slide_bottom", "fade", "slide_right", "slide_left", "slide_top"]

    for i, (character, text) in enumerate(dialogue, start=1):
        audio_file = OUTPUT_DIR / f"audio_{i}.wav"
        video_file = OUTPUT_DIR / f"video_{i}.mp4"

        create_audio_file(character, text, audio_file)
        audio_duration = AudioFileClip(str(audio_file)).duration

        create_video_with_subtitles(text, character, duration=audio_duration, output_file=str(video_file), 
                                    animation_type=animation_types[i % len(animation_types)], 
                                    is_vertical=is_vertical, title=title)

        audio_files.append(audio_file)
        video_files.append(video_file)

    return audio_files, video_files

def select_bgm(atmosphere: str) -> Path:
    bgm_files = [f for f in BGM_DIR.iterdir() if f.suffix in ('.bin', '.mp3')]
    atmosphere_keywords = set(keyword.strip().lower() for keyword in atmosphere.split('、'))

    best_match = None
    best_match_count = 0

    for bgm_file in bgm_files:
        bgm_name = bgm_file.stem.lower()
        bgm_keywords = set(bgm_name.split('_'))

        match_count = len(atmosphere_keywords.intersection(bgm_keywords))

        if match_count > best_match_count:
            best_match = bgm_file
            best_match_count = match_count

        if match_count == len(atmosphere_keywords):
            return bgm_file

    return best_match if best_match else BGM_DIR / 'default.bin'

def decode_bgm(bgm_file: Path) -> str:
    with bgm_file.open("rb") as f:
        encoded_data = f.read()

    decoded_data = base64.b64decode(encoded_data)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.write(decoded_data)
    temp_file.close()

    return temp_file.name

def combine_dialogue_clips(video_files: List[Path], audio_files: List[Path], output_file: Path, bgm_file: Path, is_vertical: bool) -> None:
    clips = [VideoFileClip(str(video)).set_audio(AudioFileClip(str(audio))) for video, audio in zip(video_files, audio_files)]

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

    bgm = AudioFileClip(str(bgm_file)).volumex(0.1)
    bgm = bgm.audio_loop(duration=final_clip.duration) if bgm.duration < final_clip.duration else bgm.subclip(0, final_clip.duration)
    bgm = bgm.audio_fadein(1).audio_fadeout(3)

    final_audio = CompositeAudioClip([final_clip.audio, bgm])
    final_clip = final_clip.set_audio(final_audio)

    temp_audiofile = OUTPUT_DIR / "final_dialogue_outputTEMP_MPY_wvf_snd.mp4"
    final_clip.write_videofile(str(output_file), codec="libx264", audio_codec="aac", bitrate="5000k", audio_bitrate="192k", temp_audiofile=str(temp_audiofile))

def clean_output_directory(directory: Path) -> None:
    if directory.exists():
        for item in directory.iterdir():
            if not item.name.startswith('.'):
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
    else:
        directory.mkdir(parents=True)

def log_parameters(args: argparse.Namespace) -> None:
    print(f"使用するパラメータ:\nURL/ファイル: {args.url_or_file}\nキャラクター1: {args.char1}\nキャラクター2: {args.char2}")
    print(f"長い対話: {'はい' if args.mode in [2, 4] else 'いいえ'}\n縦型動画: {'はい' if args.vertical else 'いいえ'}")

def process_scenario(scenario: List[Tuple[str, str]], title: str, atmosphere: str, dialogue: List[Tuple[str, str]]) -> Tuple[str, str, List[Tuple[str, str]]]:
    for item in scenario:
        if "タイトル" in item[0] and not title:
            title = item[1].strip()
        elif "雰囲気" in item[0] and not atmosphere:
            atmosphere = item[1].strip()
        else:
            dialogue.append(item)
    return title, atmosphere, dialogue

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="対話動画生成スクリプト")
    parser.add_argument("url_or_file", help="URLまたはファイルパス")
    parser.add_argument("-c1", "--char1", default="ずんだもん", help="キャラクター1 (デフォルト: ずんだもん)")
    parser.add_argument("-c2", "--char2", default="四国めたん", help="キャラクター2 (デフォルト: 四国めたん)")
    parser.add_argument("-m", "--mode", type=int, choices=[1, 2, 3, 4], default=1, help="対話モード (デフォルト: 1)")
    parser.add_argument("-v", "--vertical", action="store_true", help="縦型動画を生成")
    parser.add_argument("-b", "--bgm", help="BGMファイルのパス")
    return parser.parse_args()

def main() -> None:
    args = parse_arguments()

    if args.char1 not in CHARACTER_CONFIG or args.char2 not in CHARACTER_CONFIG:
        print("指定されたキャラクターが存在しません。デフォルトのキャラクターを使用します。")
        args.char1, args.char2 = "ずんだもん", "四国めたん"

    title = ""
    atmosphere = ""
    dialogue: List[Tuple[str, str]] = []
    scenario_generator = ScenarioGenerator()

    if args.url_or_file.endswith('.txt'):
        try:
            with open(args.url_or_file, 'r', encoding='utf-8') as f:
                content = f.read().strip().split('\n')

            print("テキストファイルの内容:")
            for line in content:
                print(line)

            for line in content:
                if "タイトル" in line and not title:
                    title = line.split(":", 1)[1].strip() if ":" in line else line.replace("タイトル", "").strip()
                elif "雰囲気" in line and not atmosphere:
                    atmosphere = line.split(":", 1)[1].strip() if ":" in line else line.replace("雰囲気", "").strip()
                else:
                    speaker, text = line.split(":", 1)
                    dialogue.append((speaker.strip(), text.strip()))
        except ValueError:
            print("シナリオを生成します。")
            log_parameters(args)
            scenario = scenario_generator.generate_scenario(args.url_or_file, args.char1, args.char2, args.mode)
            title, atmosphere, dialogue = process_scenario(scenario, title, atmosphere, dialogue)
    else:
        log_parameters(args)
        scenario = scenario_generator.generate_scenario(args.url_or_file, args.char1, args.char2, args.mode)
        title, atmosphere, dialogue = process_scenario(scenario, title, atmosphere, dialogue)

    clean_output_directory(OUTPUT_DIR)

    audio_files, video_files = create_dialogue_files(dialogue, args.vertical, title)

    bgm_file = Path(args.bgm) if args.bgm else select_bgm(atmosphere)

    if bgm_file.suffix == '.bin':
        bgm_file = Path(decode_bgm(bgm_file))

    combine_dialogue_clips(video_files, audio_files, FINAL_OUTPUT, bgm_file, args.vertical)

    if bgm_file.suffix == '.mp3' and bgm_file.parent == tempfile.gettempdir():
        bgm_file.unlink()

    print(f"対話動画が完成しました: {FINAL_OUTPUT}")

if __name__ == "__main__":
    main()
