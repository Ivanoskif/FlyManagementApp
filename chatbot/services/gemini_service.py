from __future__ import annotations

from google import genai
from google.genai import types

from chatbot.services.tools import (
    find_airports_tool,
    search_flights_tool,
    find_flight_days_tool,
)


MODEL_NAME = "gemini-3.5-flash-lite"


SYSTEM_INSTRUCTION = """
You are a flight assistant inside a Django flight management application.

You have access to tools that read real airport and flight data
from the application's Django database.

IMPORTANT RULES:

1. Never invent flights, airports, prices, schedules, airlines,
   availability, or connections.

2. For ANY request involving airport identification, use
   find_airports_tool.

3. For ANY request asking whether a flight exists, searching flights,
   comparing flights, finding the cheapest flight, fastest flight,
   direct flight or connecting flight, use search_flights_tool.

4. Never claim that a tool failed unless an actual tool response
   contains an error.

5. Never say that there are no flights before calling
   search_flights_tool.

6. Before searching flights you need:
   - exact origin airport
   - exact destination airport
   - departure date

7. If the user provides IATA codes, resolve them with
   find_airports_tool first.

8. If a city maps to multiple reasonable airports and the user's
   intended airport is ambiguous, ask the user which airport they mean.

9. If passengers are not specified, use 1.

10. If the user asks for the cheapest option, use sort_by="price".

11. If the user asks for the fastest option, use sort_by="duration".

12. If the user wants direct flights only, use max_stops=0.

13. For connecting flights clearly explain:
    - each flight segment
    - connection airport
    - connection duration
    - total journey duration
    - total price

14. Answer in the same language as the user.

15. If the user asks which days or dates in a month have available
    flights, first resolve the origin and destination airports and then
    use find_flight_days_tool.

16. Do not manually guess or calculate available flight dates.
    Availability by date must come from find_flight_days_tool.
"""


FIND_AIRPORTS_DECLARATION = types.FunctionDeclaration(
    name="find_airports_tool",
    description=(
        "Find active airports in the application's database. "
        "Use this before searching flights to resolve a city, airport "
        "name, IATA code, ICAO code or country into airport database IDs."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Airport search text such as TXL, GLA, Skopje, "
                    "London or Paris."
                ),
            },
        },
        "required": ["query"],
    },
)


SEARCH_FLIGHTS_DECLARATION = types.FunctionDeclaration(
    name="search_flights_tool",
    description=(
        "Search real available flights in the Django database between "
        "two already resolved airport IDs. Can find direct flights and "
        "routes with one connection."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "origin_airport_id": {
                "type": "integer",
                "description": "Database ID of the origin airport.",
            },
            "destination_airport_id": {
                "type": "integer",
                "description": "Database ID of the destination airport.",
            },
            "departure_date": {
                "type": "string",
                "description": "Departure date in YYYY-MM-DD format.",
            },
            "passengers": {
                "type": "integer",
                "description": "Number of passengers. Default is 1.",
            },
            "fare_class_id": {
                "type": "integer",
                "description": "Optional fare class database ID.",
            },
            "max_price": {
                "type": "number",
                "description": (
                    "Optional maximum total price in EUR for all passengers."
                ),
            },
            "max_stops": {
                "type": "integer",
                "description": (
                    "Maximum stops. Use 0 for direct flights only "
                    "and 1 to allow one connection."
                ),
            },
            "departure_after": {
                "type": "string",
                "description": "Optional earliest departure time in HH:MM.",
            },
            "arrival_before": {
                "type": "string",
                "description": "Optional latest arrival time in HH:MM.",
            },
            "sort_by": {
                "type": "string",
                "enum": ["price", "duration"],
                "description": (
                    "Use price for cheapest results or duration "
                    "for fastest results."
                ),
            },
        },
        "required": [
            "origin_airport_id",
            "destination_airport_id",
            "departure_date",
        ],
    },
)


def ask_gemini(message: str) -> str:
    message = (message or "").strip()

    if not message:
        return "Внесете порака."

    client = genai.Client()

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[GEMINI_TOOLS],
        temperature=0.2,
    )

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=message)
            ],
        )
    ]

    # Овозможуваме повеќе последователни function calls:
    # find origin -> find destination -> search flights -> final answer
    for _ in range(8):

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config,
        )

        function_calls = response.function_calls or []

        # Ако веќе не бара функција, ова е конечниот одговор.
        if not function_calls:
            if response.text:
                return response.text

            return "Не успеав да генерирам одговор."

        # Мора да го зачуваме одговорот од моделот
        # во кој се наоѓа function call.
        contents.append(
            response.candidates[0].content
        )

        function_response_parts = []

        for function_call in function_calls:

            function_name = function_call.name
            function_args = dict(function_call.args or {})

            print(
                "\nГемини побара функција:",
                function_name,
                function_args,
            )

            python_function = AVAILABLE_FUNCTIONS.get(
                function_name
            )

            if python_function is None:
                result = {
                    "error": (
                        f"Unknown function: {function_name}"
                    )
                }

            else:
                try:
                    result = python_function(
                        **function_args
                    )

                except Exception as exc:
                    result = {
                        "error": str(exc)
                    }

            print(
                "Резултат од функцијата:",
                result,
            )

            function_response_parts.append(
                types.Part.from_function_response(
                    name=function_name,
                    response={
                        "result": result
                    },
                )
            )

        # Му го враќаме резултатот на Гемини.
        contents.append(
            types.Content(
                role="user",
                parts=function_response_parts,
            )
        )

    return (
        "Не успеав да го завршам пребарувањето "
        "во дозволениот број чекори."
    )

FIND_FLIGHT_DAYS_DECLARATION = types.FunctionDeclaration(
    name="find_flight_days_tool",
    description=(
        "Find all dates in a specific month for which at least one "
        "available flight option exists between two resolved airports. "
        "Use this when the user asks which days or dates in a month "
        "have available flights."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "origin_airport_id": {
                "type": "integer",
                "description": "Database ID of the origin airport.",
            },
            "destination_airport_id": {
                "type": "integer",
                "description": "Database ID of the destination airport.",
            },
            "year": {
                "type": "integer",
                "description": "Year to search, for example 2026.",
            },
            "month": {
                "type": "integer",
                "description": "Month number from 1 to 12.",
            },
            "passengers": {
                "type": "integer",
                "description": "Number of passengers. Default is 1.",
            },
            "max_stops": {
                "type": "integer",
                "description": (
                    "Maximum number of stops. Use 0 if the user asks "
                    "for direct flights only."
                ),
            },
        },
        "required": [
            "origin_airport_id",
            "destination_airport_id",
            "year",
            "month",
        ],
    },
)



GEMINI_TOOLS = types.Tool(
    function_declarations=[
        FIND_AIRPORTS_DECLARATION,
        SEARCH_FLIGHTS_DECLARATION,
        FIND_FLIGHT_DAYS_DECLARATION,
    ]
)

AVAILABLE_FUNCTIONS = {
    "find_airports_tool": find_airports_tool,
    "search_flights_tool": search_flights_tool,
    "find_flight_days_tool": find_flight_days_tool,
}