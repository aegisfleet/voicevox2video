import base64
import os
import argparse

def encode_bgm(input_file, output_file):
    with open(input_file, "rb") as f:
        encoded = base64.b64encode(f.read())
    
    with open(output_file, "wb") as f:
        f.write(encoded)

def main():
    parser = argparse.ArgumentParser(description="Encode BGM file to base64")
    parser.add_argument("input_file", help="Path to the input BGM file")
    args = parser.parse_args()

    input_file = args.input_file
    output_file = os.path.splitext(input_file)[0] + ".bin"

    encode_bgm(input_file, output_file)
    print(f"BGM encoded and saved to {output_file}")

if __name__ == "__main__":
    main()
