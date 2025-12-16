"""
Meta Marketing API モジュール
"""
from .auth import MetaAuth
from .campaigns import CampaignManager
from .adsets import AdSetManager
from .ads import AdManager
from .insights import InsightsManager

__all__ = [
    "MetaAuth",
    "CampaignManager",
    "AdSetManager",
    "AdManager",
    "InsightsManager",
]


