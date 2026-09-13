"""WorldTune ORM package -- re-exports every table so `Base.metadata` is
complete after a single `import app.models`."""
from app.models.base import Base, EMBEDDING_DIM, UTCDateTime, utcnow
from app.models.career import JobORM, JobSkillORM, SkillMetricORM, SkillORM
from app.models.market import MarketAssetORM, MarketPriceORM, MarketSignalORM
from app.models.persona import PersonaORM, UserORM
from app.models.predictions import DISCLAIMER, PredictionORM, PredictionResultORM
from app.models.scoring import DailyRecommendationORM, WorldTuneScoreORM
from app.models.signals import NewsEventORM, SignalORM, TechnologyEventORM

__all__ = [
    "Base",
    "EMBEDDING_DIM",
    "UTCDateTime",
    "utcnow",
    "DISCLAIMER",
    "UserORM",
    "PersonaORM",
    "SignalORM",
    "NewsEventORM",
    "TechnologyEventORM",
    "MarketAssetORM",
    "MarketPriceORM",
    "MarketSignalORM",
    "JobORM",
    "SkillORM",
    "JobSkillORM",
    "SkillMetricORM",
    "PredictionORM",
    "PredictionResultORM",
    "WorldTuneScoreORM",
    "DailyRecommendationORM",
]
