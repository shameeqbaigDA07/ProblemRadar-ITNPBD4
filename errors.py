"""Error types used across Problem Radar.

Each error carries a plain-English message that is safe to show to the user.
No error message ever includes an API key.
"""


class ProblemRadarError(Exception):
    """Base class for errors the app knows how to explain to the user."""


class ConfigError(ProblemRadarError):
    """A setting is missing, for example an API key in the .env file."""


class ResearchError(ProblemRadarError):
    """Evidence could not be collected from the search services."""


class AnalysisError(ProblemRadarError):
    """Gemini could not be reached or its reply could not be used."""


class StorageError(ProblemRadarError):
    """A saved run could not be written or read."""


class ServiceUnavailableError(AnalysisError):
    """An AI service is busy, out of free quota, or does not know the model.

    The app can switch to another AI service when this happens.
    """
