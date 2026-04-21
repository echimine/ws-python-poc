#!/usr/bin/env python3
import os
import json
import sys
import requests

BASE_URL = os.getenv("LLAMA_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("LLAMA_API_KEY", "sk-no-key")  # souvent ignoré par llama.cpp
MODEL = os.getenv("LLAMA_MODEL", "gpt-3.5-turbo")  # llama.cpp ignore parfois / ou accepte un nom

CHAT_URL = f"{BASE_URL.rstrip('/')}/v1/chat/completions"


def chat_once(system:str, prompt: str, stream: bool = False) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "stream": stream,
    }

    if not stream:
        r = requests.post(CHAT_URL, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

    # Streaming (SSE): on lit ligne par ligne
    with requests.post(CHAT_URL, headers=headers, json=payload, stream=True, timeout=120) as r:
        r.raise_for_status()
        out = []
        for line in r.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8")
            # Les serveurs SSE préfixent souvent par "data: "
            if line.startswith("data: "):
                line = line[len("data: "):]

            if line.strip() == "[DONE]":
                break

            try:
                event = json.loads(line)
                delta = event["choices"][0].get("delta", {}).get("content")
                if delta:
                    out.append(delta)
                    print(delta, end="", flush=True)
            except json.JSONDecodeError:
                # Certaines implémentations envoient des lignes non-JSON
                continue

        print()  # newline final
        return "".join(out)



def execute_code_from(nl, filter_path, tools, categories):

    def read_md_file(filename: str) -> str:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
        
    use_stream = os.getenv("LLAMA_STREAM", "1") == "1"

    system_prompt = read_md_file(filter_path+".md")
    categories_memoire = "\n\nVoici les categories disponibles:\n" + "\n".join(categories) + "\n\n"
    user_input = nl
    answer = chat_once(categories_memoire + system_prompt, user_input, stream=use_stream)
    parsed_answer = json.loads(answer)
    capacite = parsed_answer.get("capacite")
    if capacite == "autre":
        answer = chat_once("Tu es un gentil assistant", user_input, stream=use_stream)
        return answer
    else:
        md_content = read_md_file("./nl_to_code/"+capacite+".md")
        answer = chat_once(md_content, user_input, stream=use_stream)
        parsed_answer = json.loads(answer)
        tool_name = parsed_answer.get("tool_name")
        arguments = parsed_answer.get("arguments", {})
        if tool_name in tools:
            return tools[tool_name](**arguments)

    if not use_stream:
        print(answer)
    return answer