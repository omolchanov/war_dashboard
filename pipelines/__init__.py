"""
Data pipelines: one module per pipeline.
"""

from pipelines.losses import LossesPipeline
from pipelines.economics import EconomicsPipeline

__all__ = ["LossesPipeline", "EconomicsPipeline"]
