import requests
import os

def read_user_dict(file_path):
    words = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            surface, pronunciation, accent_type = line.strip().split(',')
            words.append({
                'surface': surface,
                'pronunciation': pronunciation,
                'accent_type': int(accent_type)
            })
    return words

def register_user_dict(word):
    voicevox_api_host = os.getenv('VOICEVOX_API_HOST', 'localhost')
    base_url = f"http://{voicevox_api_host}:50021"
    
    response = requests.post(
        f"{base_url}/user_dict_word",
        params={
            'surface': word['surface'],
            'pronunciation': word['pronunciation'],
            'accent_type': word['accent_type']
        }
    )
    response.raise_for_status()
    return response.json()

def main():
    user_dict_file = 'user_dict/user_dict.txt'
    words = read_user_dict(user_dict_file)

    for word in words:
        try:
            result = register_user_dict(word)
            print(f"Registered: {word['surface']} - {result}")
        except requests.RequestException as e:
            print(f"Error registering {word['surface']}: {e}")

if __name__ == "__main__":
    main()
