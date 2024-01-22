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

BOT = 'gemini-pro'

def get_summary_prompt(transcript: str):
    '''Returns a prompt for the user to summarize the video transcript.'''

    return f'''
        Summarize the following CONTENT into brief sentences of key points,
        then provide complete highlighted information in a list,
        choosing an appropriate emoji for each highlight,
        using the same language as the CONTENT to respond.

        Your output should use the following format:
        ### Summary
        ### Highlights
        - [Emoji] Bullet point with complete explanation

        Transcript: {transcript}'''

def get_video_object(link: str):
    '''Returns a YouTube object for the given link.'''

    try:
        return YouTube(link)
    except RegexMatchError:
        return None

def check_video_length(video: YouTube):
    '''Returns True if the video is less than 20 minutes long.'''

    return video.length <= 20 * 60

def compute_transcript_text(video_id: str):
    '''Returns the transcript text of the video with the given id.'''

    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    for transcript in transcript_list:
        raw_transcript = transcript.fetch()
        break

    text_transcript = '\n'.join([item['text'] for item in raw_transcript])
    return text_transcript

def get_video_transcript(video: YouTube):
    '''Returns the transcript text of the given video.'''

    video_id = video.video_id
    transcript = compute_transcript_text(video_id)
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
        if not check_video_length(video):
            yield self.text_event(
                'Error: The video is longer than 20 minutes. Please provide a new video url.'
            )
            return

        try:
            transcript = get_video_transcript(video)
        except TranscriptsDisabled:
            yield self.text_event(
                'Error: Transcripts are disabled for this video. Please provide a new video url.'
            )
            return

        if len(transcript) > 30000:
            yield self.text_event(
                'Error: The transcript is too long. Please provide a new video url.'
            )
            return

        for message in relevant_subchat:
            if message.message_id == relevant_subchat[0].message_id:
                message.content = get_summary_prompt(transcript)

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
