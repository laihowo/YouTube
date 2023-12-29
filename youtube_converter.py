'''Download YouTube videos as MP4 or MP3 files.'''

import os
import ssl
from pytube import YouTube

ssl._create_default_https_context = ssl._create_unverified_context

while True:
    try:
        video_URL = input('Enter your YouTube Video URL: ')
        video_object = YouTube(video_URL)
        os.system(f'pytube {video_URL}')
        break
    except Exception as e:
        print(f'{e} \n')
