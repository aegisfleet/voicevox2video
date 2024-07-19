from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip

def combine_audio_video(video_file, audio_file, output_file="final_output.mp4"):
    # 動画と音声を読み込む
    video = VideoFileClip(video_file)
    audio = AudioFileClip(audio_file)

    # 動画の長さを音声の長さに合わせる
    video = video.set_duration(audio.duration)

    # 音声を動画に追加
    final_clip = video.set_audio(audio)

    # 結果を保存
    final_clip.write_videofile(output_file)

    print(f"音声付き動画が生成されました: {output_file}")

if __name__ == "__main__":
    combine_audio_video("output_with_subtitles.mp4", "output.wav")
