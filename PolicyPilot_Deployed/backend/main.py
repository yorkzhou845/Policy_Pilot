#%%
from datetime import datetime
import re

from ollama_client import ollama_client

from config import (
    EMB_MODEL,
    GEN_CONTEXT_WINDOW,
    GEN_MODEL,
    GEN_TOKEN_MAX,
    GUARD_MODEL,
    K,
)
from func import retrieve_context_chunks, set_user_prompt

#%%

guard_model = GUARD_MODEL
gen_model = GEN_MODEL
emb_model = EMB_MODEL

gen_context_window = GEN_CONTEXT_WINDOW
gen_token_max = GEN_TOKEN_MAX
k = K

SAFE_MESSAGE = "SAFE question/response."

#%%

syst_prompt = """
You are a policy assistant for Texas Tech University Health Sciences Center operating policies.
Your campus/location context comes from the user's campus selector.
The only supported campus/location selections are: Lubbock, Abilene, Amarillo, Dallas (including Mansfield), and Permian Basin.

For policy questions, answer using only retrieved policy excerpts from the GB10 retrieval context.
Do not use outside knowledge.
Do not guess.
Do not make up rules, procedures, deadlines, exceptions, or contact information.

Runtime context includes the user's current date, local time, time zone, and selected campus/location.
If the user asks only for the current date, current time, today's date, selected campus/location, or where you are based, answer directly from runtime context and do not use policy citations.
Use runtime context for policy answers only to interpret relative wording such as "today," "tomorrow," "this year," "current," "near me," or "my campus."
Runtime context is not policy content.
Do not use runtime context to invent policy rules, procedures, deadlines, exceptions, offices, or contact information.

Every paragraph or bullet point that contains policy information must include a source filename in parentheses, like this: (Source: op0101.pdf).

If the retrieved content does not clearly support the policy answer, say: "I do not know based on the provided policy content."

At the end of every answer based on retrieved content, include XML citation tags using this exact format:
<citation filename='actual_filename.pdf'>exact short quote</citation>

Only include XML citation tags for sources actually used in the answer.
If no sources are used, write Sources used: None and do not include XML citation tags.
Do not omit source filenames when policy sources are used.
"""

user_instruction = """
Use only the retrieved policy chunks below to answer.

Rules:
1. Keep the text answer around 500 words.
2. Include XML Citations only for retrieved chunks actually used in the answer.
3. Do not use outside knowledge.
4. Do not guess.
5. State deadlines, requirements, prohibitions, exceptions, and approval steps clearly.
6. Every paragraph or bullet point using policy information must end with the source filename in parentheses, such as (Source: op0101.pdf).
7. Use only filenames shown in the retrieved chunks.
8. End with XML citation tags only when policy sources are used.
9. For XML citations, copy the exact CITATION_XML_TO_COPY lines from the retrieved chunks you used.
10. Do not create your own XML citation quotes.
11. Do not put XML citation tags inside a markdown code block.
12. If no retrieved chunk clearly supports the answer, write exactly: I do not know based on the provided policy content. Then write Sources used: None. Do not include XML citation tags.

Required answer format:

Answer:
[Paragraph with policy information.] (Source: filename.pdf)

[Another paragraph if needed.] (Source: filename.pdf)

Sources used:
- filename.pdf

Then include the copied XML citation tags at the very end.

If no retrieved chunk clearly supports the answer:

Answer:
I do not know based on the provided policy content.

Sources used:
- None

Do not include XML citation tags when sources used is None.
"""



ALLOWED_LOCATIONS = {
    "Lubbock",
    "Abilene",
    "Amarillo",
    "Dallas (including Mansfield)",
    "Permian Basin",
}


def _allowed_location_or_default(value):
    cleaned = _clean_runtime_value(value, 80)

    for allowed_location in ALLOWED_LOCATIONS:
        if cleaned.lower() == allowed_location.lower():
            return allowed_location

    return "Lubbock"


def _clean_runtime_value(value, max_length=80):
    if value is None:
        return "Unknown"

    text = str(value)
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _:-/.,()+")
    cleaned = "".join(char if char in allowed_chars else " " for char in text)
    cleaned = " ".join(cleaned.split()).strip()

    if not cleaned:
        return "Unknown"

    return cleaned[:max_length]


def build_runtime_context_prompt(runtime_context=None):
    runtime_context = runtime_context or {}

    current_local = _clean_runtime_value(
        runtime_context.get("CurrentDateTimeLocal")
        or runtime_context.get("currentDateTimeLocal"),
        60,
    )
    current_utc = _clean_runtime_value(
        runtime_context.get("CurrentDateIsoUtc")
        or runtime_context.get("currentDateIsoUtc"),
        40,
    )
    time_zone = _clean_runtime_value(
        runtime_context.get("TimeZone")
        or runtime_context.get("timeZone"),
        80,
    )
    location = _allowed_location_or_default(
        runtime_context.get("Location")
        or runtime_context.get("location")
    )
    return f"""
Runtime context for this user:
- Current local date/time: {current_local}
- Current UTC date/time: {current_utc}
- User time zone: {time_zone}
- Selected campus/location: {location}

You are based at the selected campus/location for this conversation: {location}.
Use the user's date/time and selected campus/location only to interpret relative dates, relative times, and campus/location references in the user's question.
Runtime context is not policy content. If retrieved policy excerpts do not support the policy answer, say you do not know based on the provided policy content.
""".strip()



def _normalize_question_for_runtime_check(question):
    text = str(question or "").lower()
    text = re.sub(r"[^a-z0-9'\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_runtime_context_only_question(question):
    normalized = _normalize_question_for_runtime_check(question)

    if not normalized:
        return False

    if len(normalized.split()) > 12:
        return False

    # Policy questions about deadlines or due dates should still go through retrieval.
    if re.search(r"\b(policy|procedure|deadline|requirement|approval|approve|submit|submission|due)\b", normalized):
        return False

    runtime_phrases = [
        "what is the date today",
        "whats the date today",
        "what's the date today",
        "what is todays date",
        "what is today's date",
        "todays date",
        "today's date",
        "date today",
        "current date",
        "what date is it",
        "what day is it",
        "what day is today",
        "what is the day today",
        "what time is it",
        "current time",
        "local time",
        "date and time",
        "current date and time",
        "where are you based",
        "what city are you based in",
        "what campus are you based in",
        "what campus are you using",
        "what is your campus",
        "what is my campus",
        "selected campus",
        "selected location",
        "what is your location",
        "where are you located",
    ]

    return any(phrase in normalized for phrase in runtime_phrases)


def _runtime_value(runtime_context, *keys, default="Unknown"):
    runtime_context = runtime_context or {}
    for key in keys:
        value = runtime_context.get(key)
        if value:
            return _clean_runtime_value(value, 80)
    return default


def _format_runtime_datetime(current_local):
    if not current_local or current_local == "Unknown":
        return "Unknown", "Unknown", "Unknown"

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y, %I:%M:%S %p",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y, %I:%M %p",
        "%m/%d/%Y %I:%M %p",
    ]

    parsed = None
    for fmt in formats:
        try:
            parsed = datetime.strptime(current_local, fmt)
            break
        except ValueError:
            continue

    if parsed is None:
        return current_local, current_local, current_local

    date_text = f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
    hour_text = str(parsed.hour % 12 or 12)
    time_text = f"{hour_text}:{parsed.minute:02d} {parsed.strftime('%p')}"
    full_text = f"{date_text} {time_text}"
    return date_text, time_text, full_text


def _answer_runtime_context_question(question, runtime_context=None):
    normalized = _normalize_question_for_runtime_check(question)
    asks_location = any(word in normalized for word in ["based", "located", "location", "campus"])
    asks_time = "time" in normalized
    asks_date = any(word in normalized for word in ["date", "day", "today"])

    selected_location = _allowed_location_or_default(
        (runtime_context or {}).get("Location")
        or (runtime_context or {}).get("location")
    )

    if asks_location and not asks_date and not asks_time:
        return f"The selected campus/location is {selected_location}.\n\nSources used:\n- None"

    current_local = _runtime_value(
        runtime_context,
        "CurrentDateTimeLocal",
        "currentDateTimeLocal",
        default="Unknown",
    )
    time_zone = _runtime_value(
        runtime_context,
        "TimeZone",
        "timeZone",
        default="Unknown",
    )
    date_text, time_text, full_text = _format_runtime_datetime(current_local)

    if asks_time and not asks_date:
        first_line = f"The user's current local time is {time_text}."
    elif asks_date and not asks_time:
        first_line = f"Today is {date_text}."
    else:
        first_line = f"The user's current local date and time is {full_text}."

    return f"""{first_line}

User time zone: {time_zone}
Selected campus/location: {selected_location}

Sources used:
- None""".strip()


def _clean_citations_for_no_source_answer(answer):
    answer = str(answer or "")
    no_source = (
        "i do not know based on the provided policy content" in answer.lower()
        or re.search(r"Sources\s+used\s*:\s*(?:\r?\n\s*)?[-*]?\s*None\b", answer, re.I) is not None
    )

    if not no_source:
        return answer.strip()

    cleaned = re.sub(r"<citation\s+filename=['\"].*?['\"].*?</citation>", "", answer, flags=re.I | re.S)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


#%%

guard_rail_dic = {
    'S1': 'S1 - Violent Crimes: Responses that enable, encourage, or endorse the commission of violent crimes, including: (1) unlawful violence toward people (ex: terrorism, genocide, murder, hate-motivated violent crimes, child abuse, assault, battery, kidnapping) and (2) unlawful violence toward animals (ex: animal abuse)',

    'S2': 'S2 - Non-Violent Crimes: Responses that enable, encourage, or endorse the commission of non-violent crimes, including: (1) personal crimes (ex: labor trafficking, threats, intimidation, hate-motivated non-violent crimes), (2) financial crimes (ex: fraud, scams, money laundering), (3) property crimes (ex: theft, arson, vandalism), (4) drug crimes (ex: creating or using regulated substances), (5) weapons crimes (ex: producing unlicensed firearms), and (6) cyber crimes (ex: hacking)',

    'S3': 'S3 - Sex-Related Crimes: Responses that enable, encourage, or endorse the commission of sex-related crimes, including: (1) sex trafficking, (2) sexual assault (ex: rape), (3) sexual harassment (physical, verbal, or visual), and (4) prostitution',

    'S4': 'S4 - Child Sexual Exploitation: Responses that contain, describe, enable, encourage, or endorse the sexual abuse of children',

    'S5': "S5 - Defamation: Responses that are both verifiably false and likely to injure a living person's reputation",

    'S6': 'S6 - Specialized Advice: Responses that contain specialized financial, medical, or legal advice, or that indicate dangerous activities or objects are safe',

    'S7': "S7 - Privacy: Responses that contain sensitive, nonpublic personal information that could undermine someone's physical, digital, or financial security",

    'S8': 'S8 - Intellectual Property: Responses that may violate the intellectual property rights of any third party',

    'S9': 'S9 - Indiscriminate Weapons: Responses that enable, encourage, or endorse the creation of indiscriminate weapons, including: (1) chemical weapons (ex: nerve gas), (2) biological weapons (ex: anthrax), (3) radiological weapons (ex: cobalt bombs), (4) nuclear weapons (ex: fission bombs), and (5) high-yield explosive weapons (ex: cluster munitions)',

    'S10': 'S10 - Hate: Responses that demean or dehumanize people on the basis of their sensitive, personal characteristics (i.e., race, color, ethnicity, national origin, disability, religious affiliation, caste, sexual orientation, sex, gender identity, and/or serious disease)',

    'S11': 'S11 - Suicide & Self-Harm: Responses that enable, encourage, or endorse acts of intentional self-harm, including: (1) suicide, (2) self-injury (ex: cutting), and (3) disordered eating',

    'S12': 'S12 - Sexual Content: Responses that contain erotica',

    'S13': 'S13 - Elections: Responses that contain factually incorrect information about electoral systems and processes, including in the time, place, or manner of voting in civic elections'
}

#%%

def safe(prompt, guard_model=guard_model):
    guard_response = ollama_client.chat(
        model=guard_model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    raw = guard_response["message"]["content"].strip()

    lines = [line.strip() for line in raw.splitlines() if line.strip()]

    if not lines:
        return f"UNKNOWN guard response: {raw}"

    label = lines[0].lower()

    if label == "safe":
        return SAFE_MESSAGE

    if label == "unsafe":
        categories = []

        if len(lines) > 1:
            # Llama Guard usually returns:
            # unsafe
            # S1,S6
            category_text = ",".join(lines[1:])
            categories = [
                category.strip()
                for category in category_text.split(",")
                if category.strip()
            ]

        category_descriptions = [
            guard_rail_dic.get(category, f"{category} - Unknown category")
            for category in categories
        ]

        if category_descriptions:
            return (
                "UNSAFE question/response. "
                + " | ".join(category_descriptions)
            )

        return "UNSAFE question/response. No category returned."

    return f"UNKNOWN guard response: {raw}"

#%%

def get_answer(
        user_question,
        runtime_context=None,
        k=k,
        system_prompt=syst_prompt,
        user_instruction=user_instruction,
        guard_model=guard_model,
        gen_model=gen_model,
        emb_model=emb_model,
        gen_token_max=gen_token_max,
        gen_context_window=gen_context_window
        ):

    user_safety = safe(user_question, guard_model)

    if user_safety != SAFE_MESSAGE:
        return user_safety

    if _is_runtime_context_only_question(user_question):
        return _answer_runtime_context_question(user_question, runtime_context)

    chunks = retrieve_context_chunks(user_question, k) #retrieve top -k relevant policy chunks from GB10 vector database

    user_prompt = set_user_prompt(
        chunks=chunks,
        user_question=user_question,
        user_instruction=user_instruction,
        gen_model=gen_model,
        max_gen_token=gen_token_max
    )

    response = ollama_client.chat(#send to the LLM in GB10
        model=gen_model,
        messages=[
            {
                "role": "system",
                "content": system_prompt + "\n\n" + build_runtime_context_prompt(runtime_context)
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        options={
            "temperature": 0,
            "num_ctx": gen_context_window
        }
    )

    answer = response["message"]["content"]

    ai_safety = safe(answer, guard_model)

    if ai_safety == SAFE_MESSAGE:
        return _clean_citations_for_no_source_answer(answer)

    return ai_safety

#%%

def run_interactive_loop():
    while True:
        question = input("How can I help you? To exit type 'bye' ")

        if question.strip().lower() == "bye":
            print("Have a great day! Wreck 'Em, Red Raiders!")
            break

        answer = get_answer(question)

        print(f">>> {answer}\n")


if __name__ == "__main__":
    run_interactive_loop()

#%%
