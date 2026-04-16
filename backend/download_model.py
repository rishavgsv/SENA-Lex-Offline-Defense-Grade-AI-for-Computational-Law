import os
import urllib.request
import sys

url = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
local_dir = "models"
filename = "mistral-7b-instruct-v0.2.Q4_K_M.gguf"

os.makedirs(local_dir, exist_ok=True)
path_to_model = os.path.join(local_dir, filename)

def reporthook(count, block_size, total_size):
    if total_size > 0:
        downloaded = count * block_size
        percent = int(downloaded * 100 / total_size)
        mb_downloaded = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        sys.stdout.write(f"\rDownloading... {percent}% ({mb_downloaded:.2f} MB / {total_mb:.2f} MB)")
        sys.stdout.flush()

if not os.path.exists(path_to_model):
    print(f"Downloading {filename} to {local_dir}...")
    try:
        urllib.request.urlretrieve(url, path_to_model, reporthook)
        print("\nDownload complete! Restart your backend to load the model.")
    except Exception as e:
        print(f"\nDownload failed: {e}")
        print("\n" + "="*50)
        print("Your script environment seems to have network dropping issues.")
        print("Please download the file manually using your Web Browser here:")
        print(url)
        print("Once downloaded, just place it completely inside the 'backend/models/' folder as 'mistral-7b-instruct-v0.2.Q4_K_M.gguf'.")
        print("="*50)
else:
    print(f"Model {filename} already exists in {local_dir}.")
