

from .models import TTSEncoding, TTSModels
from .tts import TTS
from .version import __version__

__all__ = [
    "TTS",
    # "Voice",
    # "VoiceSettings",
    # "TTSEncoding",
    # "TTSModels",
    # "DEFAULT_VOICE",
    "__version__",
]

from livekit.agents import Plugin

from .log import logger


class MurfAIPlugin(Plugin):
    def __init__(self):
        super().__init__(__name__, __version__, __package__, logger)


Plugin.register_plugin(MurfAIPlugin())

# Cleanup docs of unexported modules
_module = dir()
NOT_IN_ALL = [m for m in _module if m not in __all__]

__pdoc__ = {}

for n in NOT_IN_ALL:
    __pdoc__[n] = False
