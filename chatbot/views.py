from django.shortcuts import render

# Create your views here.
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from google.genai.errors import ServerError

from chatbot.services.gemini_service import ask_gemini


logger = logging.getLogger(__name__)


@require_POST
def chat_message(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "Невалидно барање."},
            status=400,
        )

    message = (data.get("message") or "").strip()

    if not message:
        return JsonResponse(
            {"error": "Внесете порака."},
            status=400,
        )

    try:
        answer = ask_gemini(message)

        return JsonResponse({
            "answer": answer
        })

    except ServerError:
        return JsonResponse(
            {
                "error": (
                    "AI сервисот моментално е недостапен. "
                    "Обидете се повторно."
                )
            },
            status=503,
        )

    except Exception:
        logger.exception("Chatbot error")

        return JsonResponse(
            {
                "error": (
                    "Настана проблем при обработката "
                    "на прашањето."
                )
            },
            status=500,
        )