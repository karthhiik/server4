# # import base64
# # from openai import OpenAI

# # endpoint = ""
# # deployment_name = "FLUX.1-Kontext-pro"
# # api_key = ""

# # client = OpenAI(
# #     base_url=endpoint,
# #     api_key=api_key
# # )

# # img = client.images.generate(
# #     model=deployment_name,
# #     prompt="A cute baby polar bear",
# #     n=1,
# #     size="1024x1024",
# # )

# # image_bytes = base64.b64decode(img.data[0].b64_json)
# # with open("output.png", "wb") as f:
# #     f.write(image_bytes)

# from openai import OpenAI

# endpoint = "https://info-m98rto5s-eastus2.openai.azure.com/openai/v1/"
# deployment_name = "gpt-4o-mini"
# api_key = ""

# client = OpenAI(
#     base_url=endpoint,
#     api_key=api_key
# )

# completion = client.chat.completions.create(
#     model=deployment_name,
#     messages=[
#         {
#             "role": "user",
#             "content": "What is the capital of France?",
#         }
#     ],
# )

# print(completion.choices[0].message)

# # from openai import OpenAI

# # endpoint = "https://info-m98rto5s-eastus2.openai.azure.com/openai/v1/"
# # deployment_name = "Kimi-K2-Thinking"
# # api_key = ""

# # client = OpenAI(
# #     base_url=endpoint,
# #     api_key=api_key
# # )

# # completion = client.chat.completions.create(
# #     model=deployment_name,
# #     messages=[
# #         {
# #             "role": "user",
# #             "content": "What is the capital of France?",
# #         }
# #     ],
# # )

# # print(completion.choices[0].message)


# from openai import OpenAI

# endpoint = "https://info-m98rto5s-eastus2.openai.azure.com/openai/v1/"
# deployment_name = "Phi-4-reasoning"
# api_key = ""

# client = OpenAI(
#     base_url=endpoint,
#     api_key=api_key
# )

# completion = client.chat.completions.create(
#     model=deployment_name,
#     messages=[
#         {
#             "role": "user",
#             "content": "What is the capital of France?",
#         }
#     ],
# )

# print(completion.choices[0].message)
# lucid-origin 

# 🔧 CONFIGURATION
WORKER_URL = "https://lucid-originmodel.barisebotsnetworking.workers.dev"  # Replace with your actual URL
API_KEY = "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"  # Replace with your actual API key
  # Replace with your actual API key

def generate_image(prompt):
    """Generate an image using Lucid-Origin (dimensions auto-handled)"""
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt
    }
    
    try:
        response = requests.post(
            f"{WORKER_URL}/",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            # Decode base64 image
            image_data = base64.b64decode(response.content)
            
            # Save the image
            image_filename = f"generated_image_{int(time.time())}.jpg"
            with open(image_filename, "wb") as f:
                f.write(image_data)
            
            print("✅ Image generated successfully!")
            print(f"💾 Saved to: {image_filename}")
            print(f"📏 Size: {len(image_data)} bytes")
            print(f"🎨 Prompt: {prompt}")
            return image_data
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

# 🧪 Test examples
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Lucid-Origin Image Generation")
    print("=" * 60)
    
    # Test 1: Slide generation
    print("\n[Test 1] Business Presentation Slide")
    print("-" * 60)
    generate_image(
        "A professional business presentation slide with a clean layout, "
        "title 'Strategic Growth 2025', data visualization chart, "
        "modern corporate style, 16:9 aspect ratio"
    )
    
    # Test 2: Marketing slide
    print("\n[Test 2] Marketing Presentation")
    print("-" * 60)
    generate_image(
        "Marketing presentation slide with bold typography, "
        "product showcase, vibrant colors, 16:9 aspect ratio, "
        "modern design"
    )
    
    # Test 3: Creative slide
    print("\n[Test 3] Creative Presentation")
    print("-" * 60)
    generate_image(
        "Creative presentation slide with artistic gradient background, "
        "hand-drawn elements, inspiring message, 16:9 aspect ratio"
    )


