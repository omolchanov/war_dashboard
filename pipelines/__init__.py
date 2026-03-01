"""
Data pipelines: one module per pipeline.
"""

from pipelines.base import QuarterlyPipeline
from pipelines.economics import EconomicsPipeline
from pipelines.losses import LossesPipeline
from pipelines.recruiting import RecruitingPipeline

__all__ = ["EconomicsPipeline", "LossesPipeline", "QuarterlyPipeline", "RecruitingPipeline"]
