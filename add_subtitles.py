from moviepy.editor import ColorClip, ImageClip, CompositeVideoClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Union, Tuple

def create_text_image(text: str, font_size: int, font_path: str, size: Tuple[int, int], 
                      color: Union[str, Tuple[int, int, int, int]] = 'white', 
                      bg_color: Union[str, Tuple[int, int, int, int]] = 'transparent') -> np.ndarray:
    font = ImageFont.truetype(font_path, font_size)
    img = Image.new('RGBA', size, bg_color)
    draw = ImageDraw.Draw(img)
    draw.text((0, 0), text, font=font, fill=color)
    return np.array(img)

def create_video_with_subtitles(subtitle_text: str, duration: float = 5, 
                                output_file: str = "output_with_subtitles.mp4", 
                                font_path: str = "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf") -> None:
    # 背景となる単色の動画を作成
    background = ColorClip(size=(1280, 720), color=(0, 0, 0)).set_duration(duration)

    # テロップを作成
    text_img = create_text_image(subtitle_text, font_size=36, font_path=font_path, 
                                 size=(1000, 300), color='white', bg_color=(0,0,0,0))
    text_clip = ImageClip(text_img).set_duration(duration)
    text_clip = text_clip.set_position('center')

    # 背景とテロップを合成
    final_clip = CompositeVideoClip([background, text_clip])

    # 結果を保存
    final_clip.write_videofile(output_file, fps=24)

    print(f"テロップ付き動画が生成されました: {output_file}")

if __name__ == "__main__":
    create_video_with_subtitles("これはテロップのテストです。\nVOICEVOXの音声と組み合わせます。")
