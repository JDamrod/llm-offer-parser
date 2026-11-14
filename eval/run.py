from offer_parser.main import ask_llm, _clean_json, prompt, MODEL
import json
import time
from datetime import datetime
from pathlib import Path

EVAL_DIR = Path(__file__).parent
with open(EVAL_DIR / "cases.json", "r", encoding="utf-8") as f:
    cases = json.load(f)


def norm(value):
    # lower case, no spaces around, no final period
    if isinstance(value, str):
        return value.strip().lower().rstrip(".")
    return value


def field_ok(field, got, expected_value):
    # missing_fields: order does not matter
    if field == "missing_fields":
        return isinstance(got, list) and set(got) == set(expected_value)

    # available_information: None values and key order do not matter
    if field == "available_information":
        if not isinstance(got, dict):
            return False
        clean = {k: norm(v) for k, v in got.items() if v is not None}
        return clean == {k: norm(v) for k, v in expected_value.items()}

    # comment: the expected text must be inside the answer
    if field == "comment":
        if expected_value is None:
            return got is None
        return isinstance(got, str) and norm(expected_value) in norm(got)

    return norm(got) == norm(expected_value)


def ask_with_retry(messages, attempts=3):
    # rate limit / network errors should not kill the whole run
    for attempt in range(attempts):
        try:
            return ask_llm(messages)
        except Exception as e:
            print(f"⚠️ API error ({attempt + 1}/{attempts}): {e}")
            time.sleep(10)
    return None


total_cases = len(cases)

correct_actions = 0
fully_correct = 0
nonnull_total = 0      # expected fields that are not null
nonnull_correct = 0
false_positives = 0    # model returned a value, expected null
failures = []

for case in cases:

    message = case["message"]
    expected = case["expected"]

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

    answer = ask_with_retry(messages)

    try:
        result = _clean_json(answer)

        if not isinstance(result, dict):
            raise ValueError("Answer is not a JSON object")

    except Exception:
        print("❌ Invalid JSON")
        print(answer)

        # invalid answer = failed case, its expected fields count as wrong
        for field, expected_value in expected.items():
            if field in ("action", "question"):
                continue
            if expected_value is not None:
                nonnull_total += 1

        failures.append({
            "id": case.get("id"),
            "message": message,
            "problem": "invalid JSON or no answer",
            "answer": answer
        })

        time.sleep(3.1)
        continue

    # Проверка action

    action_ok = result.get("action") == expected.get("action")

    if action_ok:
        correct_actions += 1

    case_ok = action_ok
    mismatches = []


    # Проверка полей

    for field, expected_value in expected.items():

        if field == "action":
            continue
        elif field == "question":
            continue

        # wrong action: all non-null expected fields are wrong
        if not action_ok:
            if expected_value is not None:
                nonnull_total += 1
                mismatches.append({"field": field, "expected": expected_value, "got": result.get(field), 
                "reason": "action is wrong!"})
            continue

        got = result.get(field)
        ok = field_ok(field, got, expected_value)

        if expected_value is not None:
            nonnull_total += 1
            if ok:
                nonnull_correct += 1
        elif got is not None:
            false_positives += 1

        if not ok:
            case_ok = False
            mismatches.append({"field": field, "expected": expected_value, "got": got,
            "reason": "different values!"})

    if case_ok:
        fully_correct += 1
    else:
        failures.append({
            "id": case.get("id"),
            "message": message,
            "mismatches": mismatches,
            "result": result 
        })
    
    time.sleep(3.1) # gemini api-key limit



action_accuracy = correct_actions / total_cases * 100

case_accuracy = fully_correct / total_cases * 100

field_accuracy = nonnull_correct / nonnull_total * 100 if nonnull_total else 100.0

result = {
"Model": MODEL,
"Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
"Number of cases": total_cases,
"Number of correct actions": correct_actions,
"Number of fully correct cases": fully_correct,
"Number of non-null fields": nonnull_total,
"Number of correct non-null fields": nonnull_correct,
"False positives (expected None, but got value)": false_positives,
"Action accuracy": f"{action_accuracy:.2f}%",
"Case accuracy (all fields correct)": f"{case_accuracy:.2f}%",
"Field accuracy (non-null fields)": f"{field_accuracy:.2f}%",
"Failures": failures
}

(EVAL_DIR / "results").mkdir(exist_ok=True)

file_name = EVAL_DIR / f"results/results_{datetime.now().strftime('%Y-%m-%d___%H-%M-%S')}.json"

with open (file_name, "w", encoding="utf-8") as file:
    json.dump(result, file, ensure_ascii=False, indent=4)

print("\n====================")
print(f"Action accuracy: {action_accuracy:.2f}%")
print(f"Cases fully correct: {fully_correct}/{total_cases} ({case_accuracy:.2f}%)")
print(f"Non-null field accuracy: {field_accuracy:.2f}%")
print(f"False positives: {false_positives}")
print(f"Saved to {file_name}")
print("====================")