import ollama
import asyncio
from chroma_memory import build_prompt , contextual_storage


async def chat_with_ollama(user_input):
    """Sends user input to ollama bot with memory context and returns streamed responses ."""
    prompt = build_prompt(user_input)
    response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': user_input}], stream=True)

    full_response= ""
    async for chunk in response:
        await asyncio.sleep(0)
        content= chunk['message']['content']
        full_response += content
        yield content

    contextual_storage(user_input,full_response)