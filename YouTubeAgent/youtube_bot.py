'''
Starts the YouTube Bot Server and Runs a FastAPI app.
'''

import requests, threading
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
    bot_handle = 'YouTubeAgentTest'
    response = requests.post(
        f'https://api.poe.com/bot/fetch_settings/{bot_handle}/{key}',
        timeout=10,
    )
    print(response.text)

def fastapi_app():
    '''
    This function represents the FastAPI application of the bot server.
    It runs the fetch_settings function and constructs an instance of YouTubeAgent.
    Finally, it starts the bot using the access key obtained from the dotenv file.

    Parameters:
    None

    Returns:
    None
    '''

    # Poe Access Key
    key = dotenv_values()['POE_ACCESS_KEY']

    # Runs the fetch_settings function in a separate thread
    threading.Thread(
        target=fetch_settings,
        args=(key,)
    ).start()

    # Constructs the bot and starts it
    bot = YouTubeAgent()
    fp.run(bot, access_key=key)

fastapi_app()
