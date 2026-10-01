from app.core.database import Base
from app.models.ai import AIDetection, AIModel, AIProcessingRun, DamageType
from app.models.damage import DamageRecord, DamageReview
from app.models.history import AuditLog, GeneratedReport, Notification, RecurrenceRecord
from app.models.identity import (
    Organization,
    OrganizationMembership,
    Permission,
    RefreshToken,
    Role,
    User,
    role_permissions,
)
from app.models.inspection import Inspection, InspectionMedia
from app.models.intelligence import (
    DeteriorationPrediction,
    MaintenancePrioritySnapshot,
    RoadHealthSnapshot,
)
from app.models.jobs import ProcessingJob
from app.models.maintenance import (
    MaintenanceDamageLink,
    MaintenanceJob,
    MaintenanceStatusHistory,
)
from app.models.repair import RepairEvidence, RepairVerification
from app.models.road import Road, RoadSegment

__all__ = [
    "AIDetection",
    "AIModel",
    "AIProcessingRun",
    "AuditLog",
    "Base",
    "DamageRecord",
    "DamageReview",
    "DamageType",
    "DeteriorationPrediction",
    "GeneratedReport",
    "Inspection",
    "InspectionMedia",
    "MaintenanceDamageLink",
    "MaintenanceJob",
    "MaintenancePrioritySnapshot",
    "MaintenanceStatusHistory",
    "Notification",
    "Organization",
    "OrganizationMembership",
    "Permission",
    "ProcessingJob",
    "RecurrenceRecord",
    "RefreshToken",
    "RepairEvidence",
    "RepairVerification",
    "Road",
    "RoadHealthSnapshot",
    "RoadSegment",
    "Role",
    "User",
    "role_permissions",
]
