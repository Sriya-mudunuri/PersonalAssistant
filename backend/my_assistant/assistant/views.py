import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus

from django.utils import timezone

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Reminder, CommandHistory


def save_history(command, intent, response):
    CommandHistory.objects.create(
        command=command,
        intent=intent,
        response=response,
    )


def assistant_response(
    command,
    intent,
    speech,
    action="none",
    url=None,
    data=None,
):
    save_history(command, intent, speech)

    return Response(
        {
            "command": command,
            "intent": intent,
            "speech": speech,
            "action": action,
            "url": url,
            "data": data,
        }
    )


# --------------------------------------------------
# REMINDER TIME PARSER
# --------------------------------------------------

def parse_reminder_time(command):
    command = command.lower()

    now = timezone.localtime()

    # Examples:
    # 6 pm
    # 6:30 pm
    # 10 am

    match = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
        command,
    )

    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    period = match.group(3)

    if period == "pm" and hour != 12:
        hour += 12

    if period == "am" and hour == 12:
        hour = 0

    target_date = now.date()

    if "tomorrow" in command:
        target_date += timedelta(days=1)

    reminder_datetime = datetime.combine(
        target_date,
        datetime.min.time(),
    ).replace(
        hour=hour,
        minute=minute,
    )

    reminder_datetime = timezone.make_aware(
        reminder_datetime,
        timezone.get_current_timezone(),
    )

    # If user says 6 PM and today's 6 PM has already passed,
    # assume tomorrow.
    if (
        "tomorrow" not in command
        and reminder_datetime <= now
    ):
        reminder_datetime += timedelta(days=1)

    return reminder_datetime


# --------------------------------------------------
# MAIN VOICE COMMAND API
# --------------------------------------------------

@api_view(["POST"])
def command_assistant(request):

    command = request.data.get("message", "").strip()

    if not command:
        return Response(
            {"error": "Message is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    lower_command = command.lower()


    # ==================================================
    # NAVIGATION
    # ==================================================

    navigation_patterns = [
        "take me to ",
        "navigate to ",
        "directions to ",
        "route to ",
        "go to ",
    ]

    for pattern in navigation_patterns:

        if lower_command.startswith(pattern):

            destination = command[len(pattern):].strip()

            if not destination:
                break

            url = (
                "https://www.google.com/maps/dir/"
                f"?api=1&destination={quote_plus(destination)}"
            )

            return assistant_response(
                command=command,
                intent="navigation",
                speech=f"Opening directions to {destination}.",
                action="open_url",
                url=url,
            )


    # ==================================================
    # SPOTIFY
    # ==================================================

    if "spotify" in lower_command and (
        "play " in lower_command
        or "search " in lower_command
    ):

        song = re.sub(
            r"\b(play|search|on|in|spotify|for)\b",
            " ",
            command,
            flags=re.IGNORECASE,
        )

        song = " ".join(song.split())

        url = (
            "https://open.spotify.com/search/"
            + quote_plus(song)
        )

        return assistant_response(
            command=command,
            intent="spotify",
            speech=f"Searching Spotify for {song}.",
            action="open_url",
            url=url,
        )


    # ==================================================
    # YOUTUBE
    # ==================================================

    if "youtube" in lower_command:

        query = re.sub(
            r"\b(play|search|youtube|on|in|for)\b",
            " ",
            command,
            flags=re.IGNORECASE,
        )

        query = " ".join(query.split())

        url = (
            "https://www.youtube.com/results"
            f"?search_query={quote_plus(query)}"
        )

        return assistant_response(
            command=command,
            intent="youtube",
            speech=f"Searching YouTube for {query}.",
            action="open_url",
            url=url,
        )


    # ==================================================
    # REMINDER
    # ==================================================

    if (
        "remind me" in lower_command
        or lower_command.startswith("reminder")
    ):

        reminder_time = parse_reminder_time(command)

        if reminder_time is None:

            return assistant_response(
                command=command,
                intent="reminder",
                speech=(
                    "Please tell me the reminder time. "
                    "For example, remind me at 6 PM to go to the gym."
                ),
            )

        title = re.sub(
            r"remind me",
            "",
            command,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"\b(today|tomorrow)\b",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = re.sub(
            r"^\s*to\s+",
            "",
            title,
            flags=re.IGNORECASE,
        )

        title = " ".join(title.split())

        if not title:
            title = "Reminder"

        reminder = Reminder.objects.create(
            title=title,
            reminder_time=reminder_time,
        )

        formatted_time = timezone.localtime(
            reminder.reminder_time
        ).strftime("%d %B at %I:%M %p")

        return assistant_response(
            command=command,
            intent="reminder",
            speech=f"Okay. I will remind you to {title} on {formatted_time}.",
            action="reminder_created",
            data={
                "id": reminder.id,
                "title": reminder.title,
                "reminder_time": reminder.reminder_time,
            },
        )


    # ==================================================
    # SHOW REMINDERS
    # ==================================================

    if (
        "show my reminders" in lower_command
        or "what are my reminders" in lower_command
        or "my reminders" == lower_command
    ):

        reminders = Reminder.objects.filter(
            completed=False,
            reminder_time__gte=timezone.now(),
        )[:20]

        data = [
            {
                "id": reminder.id,
                "title": reminder.title,
                "reminder_time": reminder.reminder_time,
            }
            for reminder in reminders
        ]

        if not data:

            speech = "You don't have any upcoming reminders."

        else:

            speech = (
                f"You have {len(data)} upcoming "
                f"{'reminder' if len(data) == 1 else 'reminders'}."
            )

        return assistant_response(
            command=command,
            intent="get_reminders",
            speech=speech,
            action="display_reminders",
            data=data,
        )


    # ==================================================
    # OPEN WEBSITE
    # ==================================================

    if lower_command.startswith("open "):

        website = command[5:].strip()

        known_websites = {
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "spotify": "https://open.spotify.com",
            "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com",
            "github": "https://github.com",
            "linkedin": "https://www.linkedin.com",
            "gmail": "https://mail.google.com",
        }

        website_lower = website.lower()

        if website_lower in known_websites:

            url = known_websites[website_lower]

        else:

            url = (
                "https://www.google.com/search?q="
                + quote_plus(website)
            )

        return assistant_response(
            command=command,
            intent="open",
            speech=f"Opening {website}.",
            action="open_url",
            url=url,
        )


    # ==================================================
    # GOOGLE SEARCH
    # ==================================================

    search_patterns = [
        "search for ",
        "search ",
        "google ",
        "find ",
    ]

    for pattern in search_patterns:

        if lower_command.startswith(pattern):

            query = command[len(pattern):].strip()

            if not query:
                break

            url = (
                "https://www.google.com/search?q="
                + quote_plus(query)
            )

            return assistant_response(
                command=command,
                intent="search",
                speech=f"Searching for {query}.",
                action="open_url",
                url=url,
            )


    # ==================================================
    # UNKNOWN COMMAND
    # ==================================================

    google_url = (
        "https://www.google.com/search?q="
        + quote_plus(command)
    )

    return assistant_response(
        command=command,
        intent="search",
        speech=f"I'll search for {command}.",
        action="open_url",
        url=google_url,
    )


# --------------------------------------------------
# GET REMINDERS
# --------------------------------------------------

@api_view(["GET"])
def reminders(request):

    reminder_list = Reminder.objects.all()[:100]

    data = [
        {
            "id": reminder.id,
            "title": reminder.title,
            "reminder_time": reminder.reminder_time,
            "completed": reminder.completed,
            "created_at": reminder.created_at,
        }
        for reminder in reminder_list
    ]

    return Response(data)


# --------------------------------------------------
# COMMAND HISTORY
# --------------------------------------------------

@api_view(["GET"])
def history(request):

    commands = CommandHistory.objects.all()[:100]

    data = [
        {
            "id": item.id,
            "command": item.command,
            "intent": item.intent,
            "response": item.response,
            "created_at": item.created_at,
        }
        for item in commands
    ]

    return Response(data)
