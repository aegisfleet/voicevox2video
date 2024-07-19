from generate_voice import generate_voice
from add_subtitles import create_video_with_subtitles
from combine_audio_video import combine_audio_video
import os

def main():
    # 入力テキスト
    text = "これはVOICEVOXとPythonで作成した動画です。\nテキストから音声と動画を生成しています。"

    # 音声生成
    audio_file = "output.wav"
    generate_voice(text, output_file=audio_file)

    # 音声ファイルの長さを取得
    from moviepy.editor import AudioFileClip
    audio_duration = AudioFileClip(audio_file).duration

    # テロップ付き動画生成
    video_file = "output_with_subtitles.mp4"
    font_path = "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"  # Noto Sans CJK フォントのパス
    create_video_with_subtitles(text, duration=audio_duration, output_file=video_file, font_path=font_path)

    # 音声と動画を合成
    final_output = "final_output.mp4"
    combine_audio_video(video_file, audio_file, output_file=final_output)

    # 中間ファイルを削除
    os.remove(audio_file)
    os.remove(video_file)

    print(f"処理が完了しました。最終出力: {final_output}")

if __name__ == "__main__":
    main()
