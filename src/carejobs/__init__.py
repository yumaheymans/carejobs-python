"""Client and CLI for the CareJobs.Now healthcare jobs API.

Search US healthcare jobs and the pay employers post. Free, no API key, standard library only.

>>> from carejobs import CareJobs
>>> cj = CareJobs()
>>> jobs = cj.search_jobs("icu nurse", state="TX", limit=5)   # doctest: +SKIP
>>> print(jobs.text)                                           # doctest: +SKIP
"""

from ._version import __version__
from .client import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    CareJobs,
    CareJobsError,
    Result,
)
from .types import (
    CARE_TYPES,
    EMPLOYER_TYPES,
    KINDS,
    SORTS,
    Care,
    EmployerType,
    Kind,
    Sort,
)

__all__ = [
    "__version__",
    "CareJobs",
    "CareJobsError",
    "Result",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "KINDS",
    "CARE_TYPES",
    "EMPLOYER_TYPES",
    "SORTS",
    "Kind",
    "Care",
    "EmployerType",
    "Sort",
]
