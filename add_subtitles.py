import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ColorClip, ImageClip, CompositeVideoClip
from typing import Union, Tuple, Optional
import os
import textwrap

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

def create_text_image(text: str, character: str, font_size: int, font_path: str, size: Tuple[int, int],
                      color: Union[str, Tuple[int, int, int, int]] = 'white',
                      bg_color: Union[str, Tuple[int, int, int, int]] = 'transparent') -> np.ndarray:
    font = ImageFont.truetype(font_path, font_size)
    img = Image.new('RGBA', size, bg_color)
    draw = ImageDraw.Draw(img)

    lines = [character] + textwrap.wrap(text, width=30)

    _, _, _, line_height = font.getbbox("A")

    y_text = (size[1] - len(lines) * line_height) // 2 

    for i, line in enumerate(lines):
        left, top, right, bottom = font.getbbox(line)
        line_width = right - left

        x_text = (size[0] - line_width) // 2 

        if i == 0: 
            if character == "四国めたん":
                outline_color = (255, 0, 240) 
            else:
                outline_color = (0, 255, 0)  

            for offset in range(-2, 3):
                draw.text((x_text + offset, y_text), line, font=font, fill=outline_color)
                draw.text((x_text, y_text + offset), line, font=font, fill=outline_color)
            
            draw.text((x_text, y_text), line, font=font, fill=color)
        else:
            draw.text((x_text, y_text), line, font=font, fill=color)
        
        y_text += line_height

    return np.array(img)

def create_video_with_subtitles(subtitle_text: str, character: str, duration: float = 5,
                                output_file: str = "output_with_subtitles.mp4",
                                font_path: Optional[str] = None) -> None:
    if font_path is None:
        font_path = find_font()

    background = ColorClip(size=(1280, 720), color=(0, 0, 0)).set_duration(duration)

    text_img = create_text_image(subtitle_text, character, font_size=36, font_path=font_path,
                                 size=(1280, 720), color='white', bg_color=(0,0,0,128))
    text_clip = ImageClip(text_img).set_duration(duration)

    final_clip = CompositeVideoClip([background, text_clip])

    final_clip.write_videofile(output_file, fps=24)

    print(f"テロップ付き動画が生成されました: {output_file}")

if __name__ == "__main__":
    create_video_with_subtitles("これはテロップのテストです。VOICEVOXの音声と組み合わせます。", "四国めたん")
