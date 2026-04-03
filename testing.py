import base64
from openai import OpenAI

endpoint = ""
deployment_name = "FLUX.1-Kontext-pro"
api_key = ""

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

img = client.images.generate(
    model=deployment_name,
    prompt="A cute baby polar bear",
    n=1,
    size="1024x1024",
)

image_bytes = base64.b64decode(img.data[0].b64_json)
with open("output.png", "wb") as f:
    f.write(image_bytes)

from openai import OpenAI

endpoint = ""
deployment_name = "gpt-4o-mini"
api_key = ""

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
)

print(completion.choices[0].message)

from openai import OpenAI

endpoint = "https://info-m98rto5s-eastus2.openai.azure.com/openai/v1/"
deployment_name = "Kimi-K2-Thinking"
api_key = ""

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
)

print(completion.choices[0].message)


from openai import OpenAI

endpoint = ""
deployment_name = "Phi-4-reasoning"
api_key = ""

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

completion = client.chat.completions.create(
    model=deployment_name,
    messages=[
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
)

print(completion.choices[0].message)