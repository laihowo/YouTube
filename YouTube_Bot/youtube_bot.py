'''
Runs the YouTube Bot as a FastAPI app.
'''

import os, threading
from dotenv import dotenv_values

import fastapi_poe as fp
from yt_bot import YTSummarizerBot

def fetch_settings(key):
    '''Fetches the settings for the bot.'''
    os.system(f'sleep 5 && \
        curl -X POST https://api.poe.com/bot/fetch_settings/YouTubeAgent/{key}')

def fastapi_app():
    '''Parallel programming with the bot server.'''

    key = dotenv_values()['POE_ACCESS_KEY']

    # Create a thread that will run the fetch_settings function
    settings_thread = threading.Thread(target=fetch_settings, args=(key,))
    settings_thread.start()

    bot = YTSummarizerBot()
    fp.run(bot, access_key=key)

fastapi_app()
