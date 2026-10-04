
from django.urls import path
from . import views


urlpatterns = [
    path("command/",views.command_assistant,name="command_assistant",),

    path("reminders/",views.reminders,name="reminders",),

    path("reminders/<int:reminder_id>/complete/",views.complete_reminder,name="complete_reminder",),

    path("history/",views.history,name="history",),
]