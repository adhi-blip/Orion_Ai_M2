import chromadb
import uuid
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="context")



def relevant_context(user_input):
    results=collection.query(
        query_texts=[user_input],
        n_results=3
    )
    return results['documents']if results['documents']else[]

def contextual_storage(user_input,ai_response):
    unique_id= str(uuid.uuid4())

    collection.add(
        documents=[f"User:{user_input}\nAI: {ai_response}"],
        ids=[f"chat_{unique_id}"],
        metadatas=[{"source":"conversation"}]
    )
def build_prompt(user_input):
    context_list = relevant_context(user_input)
    context_text = "\n".join(context_list)
    return f"""Use the following context to answer:
{context_text}

User: {user_input}
AI:"""
#place holder commit
#place holder commit 2