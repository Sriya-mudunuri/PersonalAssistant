
"use client";

import { useEffect, useState } from "react";

type AssistantResponse = {
    command: string;
    intent: string;
    speech: string;
    action: string;
    url: string | null;
    data: unknown;
};

type Reminder = {
    id: number;
    title: string;
    reminder_time: string;
    completed: boolean;
    created_at: string;
};

export default function VoiceAssistant() {
    const [listening, setListening] = useState(false);
    const [loading, setLoading] = useState(false);

    const [command, setCommand] = useState("");
    const [assistantText, setAssistantText] = useState(
        "Tap the microphone and ask me something."
    );
    const [reminders, setReminders] = useState<Reminder[]>([]);

    // ---------------------------------------
    // FETCH REMINDERS
    // ---------------------------------------

    const fetchReminders = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL;

            if (!apiUrl) {
                return;
            }

            const response = await fetch(
                `${apiUrl}/api/assistant/reminders/`
            );

            if (!response.ok) {
                throw new Error("Unable to fetch reminders.");
            }

            const data: Reminder[] = await response.json();

            setReminders(data);
        } catch (error) {
            console.error("Reminder fetch error:", error);
        }
    };

    useEffect(() => {
        fetchReminders();
    }, []);
    const completeReminder = async (reminderId: number) => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL;

            if (!apiUrl) {
                return;
            }

            const response = await fetch(
                `${apiUrl}/api/assistant/reminders/${reminderId}/complete/`,
                {
                    method: "PATCH",
                }
            );

            if (!response.ok) {
                throw new Error("Unable to complete reminder.");
            }

            await fetchReminders();
        } catch (error) {
            console.error("Complete reminder error:", error);
        }
    };



    // ---------------------------------------
    // ASSISTANT SPEAKS
    // ---------------------------------------

    const speak = (text: string) => {
        if (!text) return;

        window.speechSynthesis.cancel();

        const speech = new SpeechSynthesisUtterance(text);

        speech.lang = "en-IN";
        speech.rate = 1;
        speech.pitch = 1;
        speech.volume = 1;

        window.speechSynthesis.speak(speech);
    };

    // ---------------------------------------
    // SEND TEXT TO DJANGO
    // ---------------------------------------

    const sendCommand = async (message: string) => {
        try {
            setLoading(true);
            setAssistantText("Processing...");

            const apiUrl = process.env.NEXT_PUBLIC_API_URL;

            if (!apiUrl) {
                throw new Error(
                    "NEXT_PUBLIC_API_URL is missing."
                );
            }

            const response = await fetch(
                `${apiUrl}/api/assistant/command/`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json",
                    },

                    body: JSON.stringify({
                        message: message,
                    }),
                }
            );

            const data: AssistantResponse =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    data.speech || "Unable to process command."
                );
            }

            console.log("Django response:", data);

            // Display response
            setAssistantText(data.speech);

            // Speak response
            speak(data.speech);

            // Refresh reminders when a new reminder is created
            if (data.action === "reminder_created") {
                await fetchReminders();
            }

            // Open URL returned by Django
            if (
                data.action === "open_url" &&
                data.url
            ) {
                setTimeout(() => {
                    window.location.href = data.url!;
                }, 1800);
            }
        } catch (error) {
            console.error(error);

            const errorMessage =
                "Sorry, I could not connect to the assistant.";

            setAssistantText(errorMessage);

            speak(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    // ---------------------------------------
    // START MICROPHONE
    // ---------------------------------------

    const startListening = () => {
        const SpeechRecognition =
            window.SpeechRecognition ||
            window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            alert(
                "Speech recognition is not supported in this browser. Please use Chrome."
            );

            return;
        }

        const recognition = new SpeechRecognition();

        recognition.lang = "en-IN";
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            setListening(true);

            setAssistantText("Listening...");
        };

        recognition.onresult = (event) => {
            const spokenText =
                event.results[0][0].transcript;

            console.log("You said:", spokenText);

            setCommand(spokenText);

            sendCommand(spokenText);
        };

        recognition.onerror = (event) => {
            console.error(
                "Speech recognition error:",
                event.error
            );

            setListening(false);

            setAssistantText(
                "I couldn't hear you. Please try again."
            );
        };

        recognition.onend = () => {
            setListening(false);
        };

        recognition.start();
    };

    return (
        <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 text-white">
            <div className="w-full max-w-lg">
                {/* Heading */}
                <div className="mb-10 text-center">
                    <p className="mb-2 text-sm text-slate-400">
                        Personal Assistant
                    </p>

                    <h1 className="text-4xl font-semibold">
                        How can I help?
                    </h1>
                </div>

                {/* Microphone */}
                <div className="flex justify-center">
                    <button
                        onClick={startListening}
                        disabled={listening || loading}
                        className={`
            flex h-32 w-32
            items-center justify-center
            rounded-full
            text-5xl
            shadow-xl
            transition-all
            ${listening
                                ? "scale-110 bg-red-500"
                                : "bg-blue-600 hover:scale-105 hover:bg-blue-500"
                            }
            disabled:cursor-not-allowed
          `}
                    >
                        🎤
                    </button>
                </div>

                {/* Status */}
                <p className="mt-5 text-center text-sm text-slate-400">
                    {listening
                        ? "Listening..."
                        : loading
                            ? "Processing..."
                            : "Tap to speak"}
                </p>

                {/* Conversation */}
                <div className="mt-10 space-y-4">
                    {/* User */}
                    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-400">
                            You
                        </p>

                        <p className="text-slate-200">
                            {command || "Your voice command will appear here."}
                        </p>
                    </div>

                    {/* Assistant */}
                    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-emerald-400">
                            Assistant
                        </p>

                        <p className="text-slate-200">
                            {assistantText}
                        </p>
                    </div>
                </div>

                {/* Upcoming Reminders */}
                <div className="mt-8">
                    <h2 className="mb-4 text-lg font-semibold">
                        Upcoming Reminders
                    </h2>

                    {reminders.length === 0 ? (
                        /* No Reminders */
                        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                            <p className="text-sm text-slate-400">
                                No reminders yet.
                            </p>
                        </div>
                    ) : (
                        /* Reminder List */
                        <div className="space-y-3">
                            {reminders.map((reminder) => {
                                const reminderDate = new Date(
                                    reminder.reminder_time
                                );

                                return (
                                    <div
                                        key={reminder.id}
                                        className="rounded-2xl border border-slate-800 bg-slate-900 p-5"
                                    >
                                        <div className="flex items-center gap-4">
                                            {/* Clock Icon */}
                                            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-slate-800 text-2xl">
                                                ⏰
                                            </div>

                                            {/* Reminder Information */}
                                            <div className="flex-1">
                                                <p className="font-medium text-white">
                                                    {reminder.title}
                                                </p>

                                                <p className="mt-1 text-sm text-slate-400">
                                                    {reminderDate.toLocaleDateString(
                                                        "en-IN",
                                                        {
                                                            day: "numeric",
                                                            month: "long",
                                                            year: "numeric",
                                                        }
                                                    )}

                                                    {" • "}

                                                    {reminderDate.toLocaleTimeString(
                                                        "en-IN",
                                                        {
                                                            hour: "2-digit",
                                                            minute: "2-digit",
                                                        }
                                                    )}
                                                </p>
                                            </div>

                                            {/* Status */}
                                            {reminder.completed ? (
                                                <span className="rounded-full bg-slate-700 px-3 py-1 text-xs font-medium text-slate-300">
                                                    ✓ Completed
                                                </span>
                                            ) : (
                                                <button
                                                    onClick={() => completeReminder(reminder.id)}
                                                    className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400 transition hover:bg-emerald-500/20"
                                                >
                                                    Mark Complete
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </main>
    );
}