from moviepy.editor import ColorClip, ImageClip, CompositeVideoClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Union, Tuple, Optional
import os

def find_font() -> str:
    possible_fonts = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
    ]

    for font_path in possible_fonts:
        if os.path.exists(font_path):
            return font_path

    raise FileNotFoundError("適切な日本語フォントが見つかりません。システムに日本語フォントがインストールされているか確認してください。")

def create_text_image(text: str, font_size: int, font_path: str, size: Tuple[int, int], 
                      color: Union[str, Tuple[int, int, int, int]] = 'white', 
                      bg_color: Union[str, Tuple[int, int, int, int]] = 'transparent') -> np.ndarray:
    font = ImageFont.truetype(font_path, font_size)
    img = Image.new('RGBA', size, bg_color)
    draw = ImageDraw.Draw(img)

    # テキストを複数行に分割
    lines = text.split('\n')

    # フォントの高さを取得
    _, _, _, line_height = font.getbbox("A")

    y_text = 0
    for line in lines:
        # 行の幅を取得
        left, top, right, bottom = font.getbbox(line)
        line_width = right - left
        
        x_text = (size[0] - line_width) / 2  # センタリング
        draw.text((x_text, y_text), line, font=font, fill=color)
        y_text += line_height

    return np.array(img)

def create_video_with_subtitles(subtitle_text: str, duration: float = 5, 
                                output_file: str = "output_with_subtitles.mp4", 
                                font_path: Optional[str] = None,
                                position: str = 'bottom') -> None:
    if font_path is None:
        font_path = find_font()

    # 背景となる単色の動画を作成
    background = ColorClip(size=(1280, 720), color=(0, 0, 0)).set_duration(duration)

    # テロップを作成
    text_img = create_text_image(subtitle_text, font_size=36, font_path=font_path, 
                                 size=(1000, 300), color='white', bg_color=(0,0,0,128))
    text_clip = ImageClip(text_img).set_duration(duration)

    # 位置を設定
    if position == 'top':
        text_position = ('center', 50)
    elif position == 'bottom':
        text_position = ('center', 570)
    else:
        text_position = 'center'

    text_clip = text_clip.set_position(text_position)

    # 背景とテロップを合成
    final_clip = CompositeVideoClip([background, text_clip])

    # 結果を保存
    final_clip.write_videofile(output_file, fps=24)

    print(f"テロップ付き動画が生成されました: {output_file}")

if __name__ == "__main__":
    create_video_with_subtitles("これはテロップのテストです。\nVOICEVOXの音声と組み合わせます。")
