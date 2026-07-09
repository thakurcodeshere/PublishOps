"""Models package — import all ORM models so Alembic and Base.metadata see them."""

from backend.models.analytics import AnalyticsSnapshot, PlatformRule, ScoringWeight
from backend.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from backend.models.collaboration import CollabTarget, FunnelStage, OutreachDraft
from backend.models.competitor import Competitor, CompetitorContent, CoverageMatrix
from backend.models.compliance import AuditTrail, ComplianceCheck, ConsentLedger
from backend.models.content import (
    AssetStage,
    AssetStatus,
    AssetType,
    BriefStatus,
    ContentAsset,
    ContentBrief,
)
from backend.models.content_arc import ArcSegment, ContentArc, ContentMixTarget
from backend.models.creator_profile import (
    AcousticProfile,
    CadenceProfile,
    CreatorProfile,
    DisfluencyProfile,
    LexicalProfile,
    OpinionEntry,
    TemporalProfile,
)
from backend.models.experiment import Experiment, ExperimentResult
from backend.models.governance import CostLedger, PipelineIncident, ServiceHealth
from backend.models.hook import Hook
from backend.models.platform_variant import PlatformVariant, VariantStatus
from backend.models.revenue import AttributionLink, ContentRevenue, RevenueEvent
from backend.models.schedule import ScheduleStatus, UploadSchedule
from backend.models.seasonal_event import EventContentPlan, SeasonalEvent
from backend.models.topic import Topic, TopicStatus
from backend.models.viral_score import ViralModelVersion, ViralScoreResult
from backend.models.vocabulary import AudiencePhrase, VocabCluster

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "Topic",
    "TopicStatus",
    "Hook",
    "ContentBrief",
    "ContentAsset",
    "BriefStatus",
    "AssetType",
    "AssetStage",
    "AssetStatus",
    "PlatformVariant",
    "VariantStatus",
    "UploadSchedule",
    "ScheduleStatus",
    "AnalyticsSnapshot",
    "ScoringWeight",
    "PlatformRule",
    "CreatorProfile",
    "LexicalProfile",
    "CadenceProfile",
    "AcousticProfile",
    "DisfluencyProfile",
    "TemporalProfile",
    "OpinionEntry",
    "Competitor",
    "CompetitorContent",
    "CoverageMatrix",
    "AudiencePhrase",
    "VocabCluster",
    "ContentArc",
    "ArcSegment",
    "ContentMixTarget",
    "ViralScoreResult",
    "ViralModelVersion",
    "ComplianceCheck",
    "ConsentLedger",
    "AuditTrail",
    "CollabTarget",
    "OutreachDraft",
    "FunnelStage",
    "SeasonalEvent",
    "EventContentPlan",
    "RevenueEvent",
    "ContentRevenue",
    "AttributionLink",
    "Experiment",
    "ExperimentResult",
    "PipelineIncident",
    "CostLedger",
    "ServiceHealth",
]
