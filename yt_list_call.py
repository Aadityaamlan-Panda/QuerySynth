import os
from yt_dlp import YoutubeDL

def download_youtube_audio(query, outdir=".", output_filename=None):
    search_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'skip_download': True,
    }
    with YoutubeDL(search_opts) as ydl:
        print(f"Searching YouTube for: {query}")
        search_url = f"ytsearch1:{query}"
        res = ydl.extract_info(search_url, download=False, process=True)
        if not res or 'entries' not in res or not res['entries']:
            raise Exception("No matching video found.")
        info = res['entries'][0]
        video_url = info['webpage_url']
        yt_title = info['title']

    # Set up named output if requested, else use default from yt-dlp
    custom_out = None
    if output_filename:
        custom_out = os.path.join(outdir, f"{output_filename}.%(ext)s")
    else:
        custom_out = os.path.join(outdir, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'outtmpl': custom_out,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }],
    }

    # Now: Download and extract the actual result filename from info-dict
    with YoutubeDL(ydl_opts) as ydl:
        print(f"Downloading audio: {yt_title}")
        info_dict = ydl.extract_info(video_url, download=True)
        # Actual output file, after postprocessor:
        filename = ydl.prepare_filename(info_dict)
        filename = os.path.splitext(filename)[0] + ".mp3"   # Always .mp3 after extraction
        print("DEBUG: File saved as:", filename)

    # Confirm file exists
    if not os.path.isfile(filename):
        # List possible files
        found = [f for f in os.listdir(outdir) if f.lower().endswith(".mp3")]
        raise Exception(
            f"Audio download failed (expected {filename}). Found: {found}"
        )

    print(f"Saved audio to: {filename}")
    return filename

if __name__ == "__main__":
    query = input("Enter YouTube song/query: ")
    mp3file = download_youtube_audio(query)
    print(f"Audio file ready: {mp3file}")
