#%%
from pathlib import Path

import ollama

from config import (
    EMB_MODEL,
    GEN_CONTEXT_WINDOW,
    GEN_MODEL,
    GEN_TOKEN_MAX,
    GUARD_MODEL,
    K,
    VECTOR_DB_CSV,
)
from func import get_embedding, get_topk_chunk, set_user_prompt

#%%

vector_db = Path(VECTOR_DB_CSV) if VECTOR_DB_CSV else None

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

You must answer using only retrieved policy excerpts from the Search tool.
Do not use outside knowledge.
Do not guess.
Do not make up rules, procedures, deadlines, exceptions, or contact information.

Every paragraph or bullet point that contains policy information must include a source filename in parentheses, like this: (Source: op0101.pdf).

If the retrieved content does not clearly support the answer, say: "I do not know based on the provided policy content."

At the end of every answer based on retrieved content, include XML citation tags using this exact format:
<citation filename='actual_filename.pdf'>exact short quote</citation>

Do not omit source filenames.
Do not omit XML citation tags.
"""

user_instruction = """
Use only the retrieved policy chunks below to answer.

Rules:
1. Keep the text answer around 500 words.
2. Always include the XML Citations at the end.
3. Do not use outside knowledge.
4. Do not guess.
5. State deadlines, requirements, prohibitions, exceptions, and approval steps clearly.
6. Every paragraph or bullet point using policy information must end with the source filename in parentheses, such as (Source: op0101.pdf).
7. Use only filenames shown in the retrieved chunks.
8. End with XML citation tags for clickable document links.
9. For XML citations, copy the exact CITATION_XML_TO_COPY lines from the retrieved chunks you used.
10. Do not create your own XML citation quotes.
11. Do not put XML citation tags inside a markdown code block.

Required answer format:

Answer:
[Paragraph with policy information.] (Source: filename.pdf)

[Another paragraph if needed.] (Source: filename.pdf)

Sources used:
- filename.pdf

Then include the copied XML citation tags at the very end.
"""

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
    guard_response = ollama.chat(
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
        k=k,
        system_prompt=syst_prompt,
        user_instruction=user_instruction,
        vector_db=vector_db,
        guard_model=guard_model,
        gen_model=gen_model,
        emb_model=emb_model,
        gen_token_max=gen_token_max,
        gen_context_window=gen_context_window
        ):

    if vector_db is None:
        return "Vector database path is blank. Fill VECTOR_DB_CSV in config.py before asking questions."

    user_safety = safe(user_question, guard_model)

    if user_safety != SAFE_MESSAGE:
        return user_safety

    user_vector = get_embedding(user_question, emb_model)

    chunks = get_topk_chunk(user_vector, vector_db, k)

    user_prompt = set_user_prompt(
        chunks=chunks,
        user_question=user_question,
        user_instruction=user_instruction,
        gen_model=gen_model,
        max_gen_token=gen_token_max
    )

    response = ollama.chat(
        model=gen_model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
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
        return answer

    return ai_safety

#%%

while True:
    question = input("How can I help you? To exit type 'bye' ")

    if question.strip().lower() == "bye":
        print("Have a great day! Wreck 'Em, Red Raiders!")
        break

    answer = get_answer(question)

    print(f">>> {answer}\n")

#%%
