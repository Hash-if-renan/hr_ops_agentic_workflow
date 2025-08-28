from __future__ import annotations

import base64
import asyncio
import os
import io
import wave
from dataclasses import dataclass

import aiohttp


from livekit.agents import (
    DEFAULT_API_CONNECT_OPTIONS,
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    tokenize,
    tts,
    utils,
)

from .log import logger

BASE_URL = "https://api.murf.ai/v1/speech/stream"
NUM_CHANNELS = 1
DEFAULT_VOICE = "en-US-natalie"
DEFAULT_SAMPLE_RATE = 44100

@dataclass
class _TTSOptions:
    voice: str
    style: str
    locale: str
    sample_rate: int
    word_tokenizer: tokenize.WordTokenizer


class TTS(tts.TTS):
    def __init__(
        self,
        *,
        voice: str = DEFAULT_VOICE,
        style: str | None = None,
        locale: str | None = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        api_key: str | None = None,
        base_url: str = BASE_URL,
        word_tokenizer: tokenize.WordTokenizer = tokenize.basic.WordTokenizer(
            ignore_punctuation=True
        ),
        http_session: aiohttp.ClientSession | None = None,
    ) -> None:
        """
        Create a new instance of Murf TTS.

        Args:
            voice (str): TTS voice to use. Defaults to "en-US-natalie".
            style (str): TTS voice style to use.
            locale(str): TTS voice locale to use. Useful for a multi-native experience
            sample_rate (int): Sample rate of audio. Defaults to 24000.
            api_key (str): Deepgram API key. If not provided, will look for DEEPGRAM_API_KEY in environment.
            base_url (str): Base URL for Deepgram TTS API. Defaults to "https://api.deepgram.com/v1/speak"
            word_tokenizer (tokenize.WordTokenizer): Tokenizer for processing text. Defaults to basic WordTokenizer.
            http_session (aiohttp.ClientSession): Optional aiohttp session to use for requests.

        """
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=sample_rate,
            num_channels=NUM_CHANNELS,
        )

        api_key = api_key or os.environ.get("MURFAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Murf AI API key required. Set MURFAI_API_KEY or provide api_key."
            )

        self._opts = _TTSOptions(
            voice=voice,
            style=style,
            locale=locale,
            sample_rate=sample_rate,
            word_tokenizer=word_tokenizer,
        )
        self._session = http_session
        self._api_key = api_key
        self._base_url = base_url

    def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = utils.http_context.http_session()
        return self._session

    def update_options(
        self,
        *,
        voice: str | None = None,
        style: str | None = None,
        locale: str | None = None,
        sample_rate: int | None = None,
    ) -> None:
        """
        args:
            model (str): TTS model to use.
            sample_rate (int): Sample rate of audio.
        """
        self._opts.voice = voice or self._opts.voice
        self._opts.style = style or self._opts.style
        self._opts.locale = locale or self._opts.locale

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "ChunkedStream":
        return ChunkedStream(
            tts=self,
            input_text=text,
            base_url=self._base_url,
            api_key=self._api_key,
            conn_options=conn_options,
            opts=self._opts,
            session=self._ensure_session(),
        )


class ChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: TTS,
        base_url: str,
        api_key: str,
        input_text: str,
        opts: _TTSOptions,
        conn_options: APIConnectOptions,
        session: aiohttp.ClientSession,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._opts = opts
        self._session = session
        self._base_url = base_url
        self._api_key = api_key

    async def _run(self) -> None:
        request_id = utils.shortuuid()

        audio_bstream = utils.audio.AudioByteStream(
            sample_rate=self._opts.sample_rate,
            num_channels=NUM_CHANNELS,
        )

        try:
            async with self._session.post(
                self._base_url,
                headers={
                    "api-key": f"{self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "text": self._input_text,
                    "voiceId" : self._opts.voice,
                    "style" : self._opts.style,
                    "multiNativeLocale" : self._opts.locale,
                    "sampleRate" : self._opts.sample_rate,
                    "channelType" : "MONO",
                    "format": "WAV"
                    },
                timeout=self._conn_options.timeout,
            ) as res:
                if res.status != 200:
                    raise APIStatusError(
                        message=res.reason or "Unknown error occurred.",
                        status_code=res.status,
                        request_id=request_id,
                        body=await res.json(),
                    )

                if not res.content_type.startswith("audio/"):
                    content = await res.text()
                    logger.error("Murf AI returned non-audio data: %s", content)
                    return

                logger.info("Text done " + self._input_text)

                header_removed = False
                buffer = b''

                async for bytes_data, _ in res.content.iter_chunks():
                    if not header_removed:
                        buffer += bytes_data
                        if len(buffer) >= 44:
                            # Skip the WAV header (first 44 bytes)
                            pcm_data = buffer[44:]
                            header_removed = True
                        else:
                            continue  # wait until we have at least 44 bytes
                    else:
                        pcm_data = bytes_data

                    for frame in audio_bstream.write(pcm_data):
                        self._event_ch.send_nowait(
                            tts.SynthesizedAudio(
                                request_id=request_id,
                                frame=frame,
                            )
                        )
                # async for bytes_data, _ in res.content.iter_chunks():
                #     for frame in audio_bstream.write(bytes_data):
                #         self._event_ch.send_nowait(
                #             tts.SynthesizedAudio(
                #                 request_id=request_id,
                #                 frame=frame,
                #             )
                #         )

                # response_json = await res.json()
                # base64_audio = response_json.get("encodedAudio")
                # audioLengthInSeconds = response_json.get("audioLengthInSeconds")
                # logger.info(f"Murf TTS :  audioLengthInSeconds: {audioLengthInSeconds} , text :  {self._input_text}" )
                # bytes_data = base64.b64decode(base64_audio, validate=True)
                #
                # with io.BytesIO(bytes_data) as wav_io:
                #     with wave.open(wav_io, 'rb') as wav_file:
                #         sample_rate = wav_file.getframerate()
                #         num_channels = wav_file.getnchannels()
                #         raw_pcm_data = wav_file.readframes(wav_file.getnframes())
                #
                # for frame in audio_bstream.write(raw_pcm_data):
                #     self._event_ch.send_nowait(
                #         tts.SynthesizedAudio(
                #             request_id=request_id,
                #             frame=frame,
                #         )
                #     )

                for frame in audio_bstream.flush():
                    self._event_ch.send_nowait(
                        tts.SynthesizedAudio(request_id=request_id, frame=frame)
                    )

        except asyncio.TimeoutError as e:
            raise APITimeoutError() from e
        except aiohttp.ClientResponseError as e:
            raise APIStatusError(
                message=e.message,
                status_code=e.status,
                request_id=request_id,
                body=None,
            ) from e
        except Exception as e:
            raise APIConnectionError() from e


