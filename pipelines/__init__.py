"""
Data pipelines: one module per pipeline.
"""

from pipelines.losses import LossesPipeline
from pipelines.economics import EconomicsPipeline
from pipelines.recruiting import RecruitingPipeline

__all__ = ["LossesPipeline", "EconomicsPipeline", "RecruitingPipeline"]
