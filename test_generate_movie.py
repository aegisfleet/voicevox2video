import unittest
from pathlib import Path
from generate_movie import create_video_with_subtitles
import shutil

class TestGenerateMovie(unittest.TestCase):
    def setUp(self):
        self.output_dir = Path("test_output")
        self.output_dir.mkdir(exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.output_dir)

    def test_create_video_with_subtitles(self):
        text = "This is a test subtitle."
        character = "TestCharacter"
        duration = 2
        output_file = str(self.output_dir / "test_video.mp4")
        animation_type = "fade"
        is_vertical = False
        title = "Test Title"

        create_video_with_subtitles(text, character, duration, output_file, animation_type, is_vertical, title)

        self.assertTrue(Path(output_file).exists())

if __name__ == '__main__':
    unittest.main()
