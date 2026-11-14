from offer_parser.main import parse_response, process_message, _clean_json
import pytest

def test_valid_action_new_offer():

    data = {
        "action": "new_offer",
        "name": "Casino",
        "geo": "IT",
        "cpa": "200 EUR"
    }

    offer = parse_response(data)

    assert offer.action == "new_offer"
    assert offer.name == "Casino"
    assert offer.geo == "IT"
    assert offer.cpa == "200 EUR"

def test_valid_action_need_more_information():

    data = {
        "action": "need_more_information",
        "available_information": {
            "geo": "IT"
        },
        "missing_fields": [
            "name",
            "cpa"
        ],
        "question": "Please provide casino name and CPA"
    }

    offer = parse_response(data)

    assert offer.action == "need_more_information"
    assert offer.available_information["geo"] == "IT"
    assert "name" in offer.missing_fields

def test_valid_action_not_new_offer():

    data = {
        "action": "not_new_offer"
    }

    offer = parse_response(data)

    assert offer.action == "not_new_offer"

def test_invalid_new_offer_missing_geo():

    data = {
        "action": "new_offer",
        "name": "Casino",
        "cpa": "100 USD"
    }

    with pytest.raises(Exception):
        parse_response(data)

def fake_llm(messages):

    if len(messages) == 2:
        return """
        {
            "action": "need_more_information",
            "available_information": {
                "name": "Lemon"
            },
            "missing_fields": [
                "geo",
                "cpa"
            ],
            "question": "Give geo and CPA"
        }
        """

    else:
        return """
        {
            "action": "new_offer",
            "name": "Lemon",
            "geo": "IT",
            "cpa": "100 USD"
        }
        """
    
def test_clarification(monkeypatch):

    monkeypatch.setattr("offer_parser.main.ask_llm", fake_llm)
    monkeypatch.setattr("builtins.input", lambda _: "IT, 100 USD")
    monkeypatch.setattr("offer_parser.main.send_to_bot", lambda _: None)

    result = process_message("Lemon")

    assert result.action == "new_offer"

def test_clean_json_plain():

    assert _clean_json('{"action": "not_new_offer"}') == {"action": "not_new_offer"}

def test_clean_json_with_markdown_fence():

    answer = """```json
    {"action": "not_new_offer"}
    ```"""

    assert _clean_json(answer) == {"action": "not_new_offer"}

def test_clean_json_invalid():

    with pytest.raises(ValueError):
        _clean_json("this is not json")