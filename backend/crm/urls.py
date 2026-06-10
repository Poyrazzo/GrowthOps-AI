from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CampaignViewSet, LeadSourceViewSet, CompanyViewSet, LeadViewSet,
    EmailAccountViewSet, LeadMagnetViewSet, MessageViewSet, ReplyViewSet,
    SuppressionListViewSet, ApprovalQueueViewSet, LinkedInTaskViewSet, AuditLogViewSet
)

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet)
router.register(r'leadsources', LeadSourceViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'leads', LeadViewSet)
router.register(r'emailaccounts', EmailAccountViewSet)
router.register(r'leadmagnets', LeadMagnetViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'replies', ReplyViewSet)
router.register(r'suppressions', SuppressionListViewSet)
router.register(r'approvals', ApprovalQueueViewSet)
router.register(r'linkedintasks', LinkedInTaskViewSet)
router.register(r'auditlogs', AuditLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
