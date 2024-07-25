import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ColorClip, ImageClip, CompositeVideoClip, vfx
import os
import json
import unicodedata

FONT_PATHS = [
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"
]
CHARACTER_DATA_FILE = "config/characters.json"
DEFAULT_COLOR = (255, 255, 255)
TITLE_SHADOW_COLOR = (50, 50, 50)
FONT_SIZE = 36
FONT_SIZE_INCREASE = 5
MARGIN_VERTICAL = 20
MARGIN_HORIZONTAL = 40
MARGIN_CHARACTER_NAME = 20
BUBBLE_RADIUS = 10
SHADOW_OFFSET = 15
NAME_OUTLINE_WIDTH = 6
ANIMATION_DURATION = 0.5
TEXT_WRAP_WIDTH_VERTICAL = 30
TEXT_WRAP_WIDTH_HORIZONTAL = 60

def load_character_data():
    with open(CHARACTER_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

CHARACTER_DATA = load_character_data()

def find_font():
    for font_path in FONT_PATHS:
        if os.path.exists(font_path):
            return font_path
    raise FileNotFoundError("適切な日本語フォントが見つかりません。")

def get_character_color(character):
    color_data = CHARACTER_DATA.get(character, {}).get("color", DEFAULT_COLOR)
    if isinstance(color_data, list) and len(color_data) >= 3:
        return tuple(map(int, color_data[:3]))
    return DEFAULT_COLOR

def is_fullwidth(char):
    return unicodedata.east_asian_width(char) in 'WF'

def wrap_text(text, width):
    lines, line, line_length = [], '', 0
    for char in text:
        char_length = 2 if is_fullwidth(char) else 1
        if line_length + char_length > width:
            lines.append(line)
            line, line_length = char, char_length
        else:
            line += char
            line_length += char_length
    if line:
        lines.append(line)
    return lines

def draw_bubble_with_shadow(draw, x, y, width, height, shadow_color, bubble_color):
    draw.rounded_rectangle([x + SHADOW_OFFSET, y + SHADOW_OFFSET, 
                            x + width + SHADOW_OFFSET, y + height + SHADOW_OFFSET],
                           radius=BUBBLE_RADIUS, fill=shadow_color)
    draw.rounded_rectangle([x, y, x + width, y + height],
                           radius=BUBBLE_RADIUS, fill=bubble_color, outline=bubble_color, width=2)

def draw_character_name(draw, character, font, x, y, outline_color, text_color):
    name_pos = (x - font.getbbox(character)[2] // 2, y)
    for offset_x in range(-NAME_OUTLINE_WIDTH, NAME_OUTLINE_WIDTH + 1):
        for offset_y in range(-NAME_OUTLINE_WIDTH, NAME_OUTLINE_WIDTH + 1):
            if offset_x != 0 or offset_y != 0:
                draw.text((name_pos[0] + offset_x, name_pos[1] + offset_y), character, font=font, fill=outline_color)
    draw.text(name_pos, character, font=font, fill=text_color)

def create_text_image(text, character, font_size, font_path, size, is_vertical=False):
    font = ImageFont.truetype(font_path, font_size)
    character_font = ImageFont.truetype(font_path, font_size + FONT_SIZE_INCREASE)
    img = Image.new('RGB', size, (0, 0, 0))
    draw = ImageDraw.Draw(img)

    character_color = tuple(int(c * 0.8) for c in get_character_color(character))
    shadow_color = tuple(int(c * 0.4) for c in get_character_color(character))
    text_color = DEFAULT_COLOR

    lines = wrap_text(text, width=TEXT_WRAP_WIDTH_VERTICAL if is_vertical else TEXT_WRAP_WIDTH_HORIZONTAL)

    line_height = font.getbbox("A")[3]
    text_width = max(font.getbbox(line)[2] for line in lines)
    text_height = len(lines) * line_height

    bubble_width = text_width + MARGIN_HORIZONTAL * 2
    bubble_height = text_height + MARGIN_VERTICAL * 3

    bubble_x = (size[0] - bubble_width) // 2
    bubble_y = (size[1] - bubble_height) // 2

    name_x, name_y = size[0] // 2, bubble_y - character_font.getbbox(character)[3] - MARGIN_VERTICAL - MARGIN_CHARACTER_NAME

    draw_bubble_with_shadow(draw, bubble_x, bubble_y, bubble_width, bubble_height, shadow_color, character_color)

    x_text, y_text = bubble_x + MARGIN_HORIZONTAL, bubble_y + MARGIN_VERTICAL
    for line in lines:
        draw.text((x_text, y_text), line, font=font, fill=text_color)
        y_text += line_height

    draw_character_name(draw, character, character_font, name_x, name_y, character_color, text_color)

    return np.array(img)

def create_title_image(title, font_path, font_size, size, character):
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.truetype(font_path, font_size + FONT_SIZE_INCREASE)

    title_lines = wrap_text(title, width=TEXT_WRAP_WIDTH_VERTICAL if size[0] < size[1] else TEXT_WRAP_WIDTH_HORIZONTAL)
    line_height = title_font.getbbox("A")[3]
    fixed_title_y = 60

    for i, line in enumerate(title_lines):
        title_width = title_font.getbbox(line)[2]
        title_x = (size[0] - title_width) // 2
        title_pos = (title_x, fixed_title_y + i * line_height)

        for offset_x in range(-2, 3):
            for offset_y in range(-2, 3):
                if offset_x != 0 or offset_y != 0:
                    draw.text((title_pos[0] + offset_x, title_pos[1] + offset_y), line, font=title_font, fill=TITLE_SHADOW_COLOR)

        draw.text(title_pos, line, font=title_font, fill=DEFAULT_COLOR)

    return np.array(img)

def add_animation(clip, animation_type, duration, is_vertical=False):
    clip = clip.fx(vfx.fadeout, duration=ANIMATION_DURATION).fx(vfx.fadein, duration=ANIMATION_DURATION)
    if animation_type == "fade":
        return clip

    axis = 1 if is_vertical else 0
    size = 1280 if axis == 0 else 720

    animations = {
        "slide_right": lambda t: (0, min(0, size * (t/ANIMATION_DURATION - 1))),
        "slide_left": lambda t: (0, max(0, size * (1 - t/ANIMATION_DURATION))),
        "slide_top": lambda t: (max(0, size * (1 - t/ANIMATION_DURATION)), 0),
        "slide_bottom": lambda t: (min(0, size * (t/ANIMATION_DURATION - 1)), 0)
    }

    return clip.set_position(animations.get(animation_type, lambda t: (0, 0)))

def create_video_with_subtitles(subtitle_text, character, duration=5, output_file="output_with_subtitles.mp4",
                                font_path=None, animation_type="fade", is_vertical=False, title=""):
    if font_path is None:
        font_path = find_font()

    size = (720, 1280) if is_vertical else (1280, 720)

    background = ColorClip(size=size, color=(0, 0, 0)).set_duration(duration)
    text_img = create_text_image(subtitle_text, character, FONT_SIZE, font_path, size, is_vertical)
    text_clip = ImageClip(text_img).set_duration(duration)
    animated_text_clip = add_animation(text_clip, animation_type, duration, is_vertical)

    clips = [background, animated_text_clip]

    if title:
        title_img = create_title_image(title, font_path, FONT_SIZE, size, character)
        title_clip = ImageClip(title_img).set_duration(duration)
        clips.append(title_clip)

    final_clip = CompositeVideoClip(clips)
    final_clip.write_videofile(output_file, fps=24)

    print(f"テロップ付き動画が生成されました: {output_file}")

if __name__ == "__main__":
    create_video_with_subtitles("これはテロップのテストです。VOICEVOXの音声と組み合わせます。", "四国めたん", 
                                duration=5, output_file="tmp/sample_landscape.mp4", is_vertical=False,
                                title="テストタイトル")
    create_video_with_subtitles("これはテロップのテストです。VOICEVOXの音声と組み合わせます。", "四国めたん", 
                                duration=5, output_file="tmp/sample_portrait.mp4", is_vertical=True,
                                title="テストタイトル")
