
from django.urls import path
from . import views


urlpatterns = [
    path("command/",views.command_assistant,name="command_assistant",),

    path("reminders/",views.reminders,name="reminders",),

    path("history/",views.history,name="history",),
]