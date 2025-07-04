import os, json, time, logging
from openai import OpenAI
from .tools import TOOL_DEFINITIONS
from .registry import list_instances
from .tools.pg_manager import fresh_clone_and_launch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

client = OpenAI()

def run_llm_loop(prompt: str):
    # boot postgres if nothing running
    if not list_instances():
        fresh_clone_and_launch("default")

    messages = [{"role": "user", "content": prompt}]
    while True:
        logging.info("Calling LLM...")
        response = client.responses.create(
            model="gpt-4.1",
            input=messages,
            tools=TOOL_DEFINITIONS
        )
        assistant_msg = response.output
        messages.append({"role": "assistant", "content": assistant_msg})
        print(assistant_msg)

        # break simple loop if LLM says done
        if "done" in assistant_msg.lower():
            break
