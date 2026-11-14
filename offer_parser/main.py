from openai import OpenAI, OpenAIError
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from offer_parser.offer_formatter import build_offer_text, send_to_bot
from pydantic import BaseModel, ConfigDict
from typing import Literal

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY", "")

client = OpenAI(
    api_key= api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

MODEL = "gemini-3.5-flash-lite"

PROMPT_PATH = Path(__file__).parent / "prompts" / "system_prompt.txt"

with open (PROMPT_PATH, "r", encoding="utf-8") as f:
    prompt = f.read()

class NewOffer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["new_offer"]
    name: str
    geo: str
    cpa: str
    source: str | None = None
    mindep: str | None = None
    cap: str | None = None
    baseline: str | None = None
    wager: str | None = None
    kpi: str | None = None
    i2r: str | None = None
    r2d: str | None = None
    platform: str | None = None
    approach: str | None = None
    comment: str | None = None

class NeedMoreInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["need_more_information"]
    available_information : dict[str, str | None]
    missing_fields: list[str]
    question: str
    
class NotNewOffer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["not_new_offer"]

def _clean_json(answer: str):
    answer = answer.replace("```json", "")
    answer = answer.replace("```", "")
    return json.loads(answer.strip())

def ask_llm (messages: list[dict[str, str]]) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages
    )

    return response.choices[0].message.content

def parse_response(data: dict):

    try:
        match data.get("action"):
            case "new_offer":
                return NewOffer(**data)

            case "need_more_information":
                return NeedMoreInfo(**data)

            case "not_new_offer":
                return NotNewOffer(**data)

            case _:
                raise ValueError("Unknown action")

    except Exception as e:
        raise e

def process_message(message):
    messages = [
        {
            "role": "system",
            "content": prompt
        },
        {
            "role": "user",
            "content": message
        }
    ]

    answer = ask_llm(messages)

    messages.append({
        "role": "assistant",
        "content": answer
    })
    
    data = _clean_json(answer)

    offer = parse_response(data)

    while offer.action == "need_more_information":

        print(offer.question)

        user_answer = input("> ")

        messages.append({
            "role": "user",
            "content": user_answer
        })

        answer = ask_llm(messages)

        messages.append({
            "role": "assistant",
            "content": answer
        })

        data = _clean_json(answer)

        offer = parse_response(data)

    if offer.action == "new_offer":
        text = build_offer_text(
        name_input=offer.name,
        geo=offer.geo,
        cpa=offer.cpa,
        source=offer.source or "FB",
        mindep=offer.mindep,
        cap=offer.cap,
        baseline=offer.baseline,
        wager=offer.wager,
        kpi=offer.kpi,
        i2r=offer.i2r,
        r2d=offer.r2d,
        platform=offer.platform,
        approach=offer.approach or "Slot",
        comment=offer.comment)

        send_to_bot(text)

        return offer

    elif offer.action == "not_new_offer":
        print("It's not new offer!")   

        return offer
    
def main ():
    print ("Введите сообщение: ")
    message = sys.stdin.read()

    try:
        process_message(message=message)
    except OpenAIError as e:
        print(f"Ошибка запроса к модели: {e}")
    except ValueError as e:
        print(f"Не удалось обработать ответ модели: {e}")
    except RuntimeError as e:
        print(f"Ошибка отправки в Telegram: {e}")

if __name__ == "__main__":
    main()