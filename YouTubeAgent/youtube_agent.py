'''
Bot that scrapes Youtube transcripts and gives summaries.
'''

from typing import AsyncIterable

from fastapi_poe import PoeBot
from fastapi_poe.client import MetaMessage, stream_request
from fastapi_poe.types import (
    ProtocolMessage,
    QueryRequest,
    SettingsRequest,
    SettingsResponse,
)

from pytube import YouTube
from pytube.helpers import RegexMatchError
from sse_starlette.sse import ServerSentEvent
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled

from deep_translator import GoogleTranslator
translator = GoogleTranslator(source='auto')

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Use the application default credentials
cred = credentials.Certificate('YouTubeAgent/benny-lai-firebase-adminsdk-jr0wc-15e8c34629.json')
app = firebase_admin.initialize_app(cred)
db = firestore.client()
responses = {}

BOT = 'gemini-pro'
ERROR_DURATION = 'Error: The video is longer than 20 minutes. Please provide a new video url. '
ERROR_DISABLED = 'Error: Transcripts are disabled for this video. Please provide a new video url. '
ERROR_LENGTHY = 'Error: The transcript is too long. Please provide a new video url. '

def get_summary_prompt(transcript: str):
    '''Returns a prompt for the user to summarize the video transcript.'''

    prompt = '''Summarize the following CONTENT into brief sentences of key points,
        then provide complete highlighted information in a list,
        choosing an appropriate emoji for each highlight.

        Your output should use the following format:
        ### Summary
        ### Highlights
        - [Emoji] Bullet point with complete explanation'''

    return f'{translator.translate(prompt)} \n {transcript}'

def get_video_object(link: str):
    '''Returns a YouTube object for the given link.'''

    try:
        return YouTube(link)
    except RegexMatchError:
        return None

def check_video_length(video: YouTube):
    '''Returns True if the video is less than 20 minutes long.'''

    return video.length <= 20 * 60

def compute_transcript_text(video_id: str, video_title: str):
    '''Returns the transcript text of the video with the given id.'''

    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    for transcript in transcript_list:
        language_code = transcript.language_code
        if 'zh' in language_code:
            language_code = 'zh-TW'
        translator.target = language_code

        raw_transcript = transcript.fetch()
        break

    text_transcript = video_title + '\n'
    text_transcript += '\n'.join([item['text'] for item in raw_transcript])
    return text_transcript

def get_video_transcript(video: YouTube):
    '''Returns the transcript text of the given video.'''

    video_id = video.video_id
    video_title = video.title
    transcript = compute_transcript_text(video_id, video_title)
    return transcript

def _get_relevant_subchat(query: QueryRequest) -> list[ProtocolMessage]:
    '''Returns the subChat of the query that contains the YouTube link.'''

    subchat = []
    for message in reversed(query.query):
        subchat.append(message)
        if message.role == 'user' and (
            message.content.startswith('http://')
            or message.content.startswith('https://')
        ):
            return list(reversed(subchat))
    return []

class YouTubeAgent(PoeBot):
    '''Bot that scrapes Youtube transcripts and gives summaries.'''

    async def get_response(self, request: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        '''Returns a summary of the video transcript.'''

        relevant_subchat = _get_relevant_subchat(request)
        if not relevant_subchat:
            yield self.text_event(
                'Please provide a link to the Youtube video you would like me to summarize.'
            )
            return

        video_message = relevant_subchat[0]
        video = YouTube(video_message.content)

        doc_ref = db.collection('responses').document()
        responses['URL'] = video_message.content
        responses['Timestamp'] = datetime.fromtimestamp(video_message.timestamp / 1_000_000)
        responses['Summary'] = ''

        if not check_video_length(video):
            yield self.text_event(ERROR_DURATION)
            responses['Summary'] += ERROR_DURATION
            doc_ref.set(responses)
            return

        try:
            transcript = get_video_transcript(video)
        except TranscriptsDisabled:
            yield self.text_event(ERROR_DISABLED)
            responses['Summary'] += ERROR_DISABLED
            doc_ref.set(responses)
            return

        if len(transcript) > 30000:
            yield self.text_event(ERROR_LENGTHY)
            responses['Summary'] += ERROR_LENGTHY
            doc_ref.set(responses)
            return

        for message in relevant_subchat:
            if message.message_id == relevant_subchat[0].message_id:
                message.content = get_summary_prompt(transcript)
                responses['Prompt'] = message.content

        request.query = relevant_subchat
        async for msg in stream_request(request, BOT, request.access_key):
            if isinstance(msg, MetaMessage):
                continue
            if msg.is_suggested_reply:
                yield self.suggested_reply_event(msg.text)
            elif msg.is_replace_response:
                yield self.replace_response_event(msg.text)
            else:
                yield self.text_event(msg.text)
                responses['Summary'] += msg.text
                doc_ref.set(responses)

    async def get_settings(self, setting: SettingsRequest) -> SettingsResponse:
        '''Returns the settings for the bot.'''

        return SettingsResponse(
            introduction_message=(
                'Hi, I am YouTube Agent. Please provide a YouTube link for the '
                'English or Chinese video that is up to 20 minutes and '
                'let me highlight the key points for you. '
                '您好，我是 YouTube Agent。請提供一條最長 20 分鐘的英文或中文 YouTube 影片連結，讓我為您抽取重點。'
            ),
            server_bot_dependencies={ BOT: 10 },
        )
