import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

load_dotenv()

async def test_deployments():
    client = AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2024-02-01"
    )
    
    deployments = {
        "Nano": os.getenv("AZURE_OPENAI_GPT4.1_NANO_DEPLOYMENT", "gpt-4.1-nano"),
        "Mini": os.getenv("AZURE_OPENAI_GPT4.1_MINI_DEPLOYMENT", "gpt-4.1-mini"),
        "GPT-4.1": os.getenv("AZURE_OPENAI_GPT4.1_DEPLOYMENT", "gpt-4.1"),
    }
    
    embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    print("Testing Azure OpenAI Deployments...\n")

    for name, deployment in deployments.items():
        print(f"Testing Chat Model [{name}]: '{deployment}'")
        try:
            response = await client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": "Reply exactly with the word: hello"}],
                max_tokens=5,
                temperature=0.0
            )
            print(f"✅ Success! Response: {response.choices[0].message.content.strip()}")
        except Exception as e:
            print(f"❌ Failed: {e}")
        print("-" * 50)

    print(f"Testing Embedding Model: '{embedding_deployment}'")
    try:
        response = await client.embeddings.create(
            input=["Test embedding generation"],
            model=embedding_deployment
        )
        print(f"✅ Success! Generated vector of length {len(response.data[0].embedding)}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    print("-" * 50)

    await client.close()

if __name__ == "__main__":
    asyncio.run(test_deployments())
