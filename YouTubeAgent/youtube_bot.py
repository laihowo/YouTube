'''
Runs the YouTube Bot as a FastAPI app.
'''

import os, threading, requests
from dotenv import dotenv_values

import fastapi_poe as fp
from youtube_agent import YouTubeAgent

def fetch_settings(key):
    '''Fetches and Updates the settings for the bot.

    Args:
        key (str): The API key for authentication.

    Returns:
        None
    '''
    response = requests.post(
        f'https://api.poe.com/bot/fetch_settings/YouTubeAgent/{key}',
        timeout=10,
    )
    print(response.text)

def fastapi_app():
    '''
    This function represents the FastAPI application for parallel programming with the bot server.
    It creates a thread to run the fetch_settings function and
    initializes an instance of YouTubeAgent.
    Finally, it runs the bot using the access key obtained from the dotenv file.

    Parameters:
    None

    Returns:
    None
    '''

    key = dotenv_values()['POE_ACCESS_KEY']

    # Create a thread that will run the fetch_settings function
    settings_thread = threading.Thread(target=fetch_settings, args=(key,))
    settings_thread.start()

    bot = YouTubeAgent()
    fp.run(bot, access_key=key)

fastapi_app()
