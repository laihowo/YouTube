from dotenv import dotenv_values

import fastapi_poe as fp
from yt_bot import YTSummarizerBot

def fastapi_app():
    bot = YTSummarizerBot()
    fp.run(bot, access_key=dotenv_values()['POE_ACCESS_KEY'])

fastapi_app()
