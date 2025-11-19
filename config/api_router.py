from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from crm.leads.api.export_views import ExportViewSet
from crm.leads.api.metrics import MetricsViewSet
from crm.leads.api.views import (
    ActivityViewSet,
    ApiCredentialViewSet,
    CategoryViewSet,
    ContactViewSet,
    ConversationViewSet,
    EmailTemplateViewSet,
    LeadStatusViewSet,
    LeadViewSet,
    MessageViewSet,
    SavedFilterViewSet,
    TagViewSet,
    TaskViewSet,
)
from crm.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)

# Leads app endpoints
router.register("categories", CategoryViewSet, basename="category")
router.register("lead-statuses", LeadStatusViewSet, basename="leadstatus")
router.register("tags", TagViewSet, basename="tag")
router.register("leads", LeadViewSet, basename="lead")
router.register("contacts", ContactViewSet, basename="contact")
router.register("activities", ActivityViewSet, basename="activity")
router.register("tasks", TaskViewSet, basename="task")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("messages", MessageViewSet, basename="message")
router.register("email-templates", EmailTemplateViewSet, basename="emailtemplate")
router.register("saved-filters", SavedFilterViewSet, basename="savedfilter")
router.register("api-credentials", ApiCredentialViewSet, basename="apicredential")

# Metrics endpoints
router.register("metrics", MetricsViewSet, basename="metrics")

# Export endpoints
router.register("exports", ExportViewSet, basename="export")


app_name = "api"
urlpatterns = router.urls
