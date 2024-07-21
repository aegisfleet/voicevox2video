import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ColorClip, ImageClip, CompositeVideoClip, vfx
from typing import Union, Tuple, Optional
import os
import unicodedata

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

def get_character_color(character: str) -> Tuple[int, int, int]:
    color_map = {
        "四国めたん": (255, 0, 240),  # ピンク
        "ずんだもん": (0, 255, 0),    # 緑
        "春日部つむぎ": (255, 165, 0),  # オレンジ
        "雨晴はう": (0, 191, 255),    # ディープスカイブルー
        "波音リツ": (255, 0, 0),      # 赤
        "玄野武宏": (0, 0, 255),      # 青
        "白上虎太郎": (255, 215, 0),   # 金
        "青山龍星": (138, 43, 226),   # ブルーバイオレット
        "冥鳴ひまり": (75, 0, 130),    # インディゴ
        "もち子さん": (255, 192, 203), # ピンク
        "剣崎雌雄": (0, 128, 0),      # グリーン
    }
    return color_map.get(character, (255, 255, 255))

def is_fullwidth(char: str) -> bool:
    return unicodedata.east_asian_width(char) in 'WF'

def wrap_text(text: str, width: int) -> list:
    lines = []
    line = ''
    line_length = 0

    for char in text:
        if is_fullwidth(char):
            char_length = 2
        else:
            char_length = 1

        if line_length + char_length > width:
            lines.append(line)
            line = char
            line_length = char_length
        else:
            line += char
            line_length += char_length

    if line:
        lines.append(line)

    return lines

def create_text_image(text: str, character: str, font_size: int, font_path: str, size: Tuple[int, int],
                      is_vertical: bool = False) -> np.ndarray:
    font = ImageFont.truetype(font_path, font_size)
    character_font_size = font_size + 5
    character_font = ImageFont.truetype(font_path, character_font_size)

    img = Image.new('RGB', size, (0, 0, 0))
    draw = ImageDraw.Draw(img)

    text_color = (255, 255, 255)
    character_color = tuple(int(c * 0.8) for c in get_character_color(character))
    shadow_color = tuple(int(c * 0.4) for c in get_character_color(character))

    if is_vertical:
        lines = wrap_text(text, width=30)
    else:
        lines = wrap_text(text, width=60)

    _, _, _, line_height = font.getbbox("A")

    text_width = max(font.getbbox(line)[2] for line in lines)
    text_height = len(lines) * line_height

    margin_vertical = 20
    margin_horizontal = 40
    margin_character_name = 20

    bubble_width = text_width + margin_horizontal * 2
    bubble_height = text_height + margin_vertical * 3

    bubble_x = (size[0] - bubble_width) // 2
    bubble_y = (size[1] - bubble_height) // 2 + font_size + margin_vertical + margin_character_name

    name_x = size[0] // 2
    name_y = bubble_y - character_font_size - margin_vertical - margin_character_name

    shadow_offset = 15
    draw.rounded_rectangle([bubble_x + shadow_offset, bubble_y + shadow_offset, 
                            bubble_x + bubble_width + shadow_offset, bubble_y + bubble_height + shadow_offset],
                           radius=10, fill=shadow_color)

    bubble_color = character_color
    draw.rounded_rectangle([bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height],
                           radius=10, fill=bubble_color, outline=character_color, width=2)

    x_text = bubble_x + margin_horizontal
    y_text = bubble_y + margin_vertical

    outline_width = 0.1

    for line in lines:
        for offset_x in np.arange(-outline_width, outline_width + 0.1):
            for offset_y in np.arange(-outline_width, outline_width + 0.1):
                if offset_x != 0 or offset_y != 0:
                    draw.text((x_text + offset_x, y_text + offset_y), line, font=font, fill=text_color)
        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += line_height

    name_width, name_height = character_font.getbbox(character)[2:]
    outline_color = character_color

    name_pos = (name_x - name_width // 2, name_y)

    name_outline_width = 6

    for offset_x in range(-name_outline_width, name_outline_width + 1):
        for offset_y in range(-name_outline_width, name_outline_width + 1):
            if offset_x != 0 or offset_y != 0:
                draw.text((name_pos[0] + offset_x, name_pos[1] + offset_y), character, font=character_font, fill=outline_color)

    draw.text(name_pos, character, font=character_font, fill=text_color)

    return np.array(img)

def add_animation(clip, animation_type: str, duration: float, is_vertical: bool = False) -> ImageClip:
    if (animation_type == "fade"):
        return clip.fx(vfx.fadeout, duration=0.5).fx(vfx.fadein, duration=0.5)
    elif (animation_type == "slide_right"):
        if (is_vertical):
            return clip.set_position(lambda t: (0, min(0, 1280 * (t/0.5 - 1))))
        else:
            return clip.set_position(lambda t: (min(0, 1280 * (t/0.5 - 1)), 0))
    elif (animation_type == "slide_left"):
        if (is_vertical):
            return clip.set_position(lambda t: (0, max(0, 1280 * (1 - t/0.5))))
        else:
            return clip.set_position(lambda t: (max(0, 1280 * (1 - t/0.5)), 0))
    elif (animation_type == "slide_top"):
        if (is_vertical):
            return clip.set_position(lambda t: (max(0, 720 * (1 - t/0.5)), 0))
        else:
            return clip.set_position(lambda t: (0, min(0, 720 * (t/0.5 - 1))))
    elif (animation_type == "slide_bottom"):
        if (is_vertical):
            return clip.set_position(lambda t: (min(0, 720 * (t/0.5 - 1)), 0))
        else:
            return clip.set_position(lambda t: (0, max(0, 720 * (1 - t/0.5))))
    else:
        return clip

def create_video_with_subtitles(subtitle_text: str, character: str, duration: float = 5,
                                output_file: str = "output_with_subtitles.mp4",
                                font_path: Optional[str] = None,
                                animation_type: str = "fade",
                                is_vertical: bool = False) -> None:
    if font_path is None:
        font_path = find_font()

    if is_vertical:
        size = (720, 1280)
        font_size = 36
    else:
        size = (1280, 720)
        font_size = 36

    background = ColorClip(size=size, color=(0, 0, 0)).set_duration(duration)

    text_img = create_text_image(subtitle_text, character, font_size=font_size, font_path=font_path,
                                 size=size, is_vertical=is_vertical)
    text_clip = ImageClip(text_img).set_duration(duration)

    animated_text_clip = add_animation(text_clip, animation_type, duration, is_vertical)

    final_clip = CompositeVideoClip([background, animated_text_clip])

    final_clip.write_videofile(output_file, fps=24)

    print(f"テロップ付き動画が生成されました: {output_file}")

if __name__ == "__main__":
    create_video_with_subtitles("これはテロップのテストです。VOICEVOXの音声と組み合わせます。", "四国めたん", duration=5, animation_type="slide_right", is_vertical=True)
