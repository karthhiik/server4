
# ## phoenix-1.0

# import requests

# # Your worker endpoint
# url = "https://image-generation.adepuvishal18.workers.dev/"

# headers = {
#     "Authorization": "Bearer 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",
#     "Content-Type": "application/json"
# }

# data = {
#     "prompt": "futuristic AI robot standing in neon cyberpunk city"
# }

# print("Sending request...")

# response = requests.post(url, json=data, headers=headers)

# print("Status Code:", response.status_code)
# print("Content-Type:", response.headers.get("content-type"))

# # If error occurs
# if response.status_code != 200:
#     print("Error Response:")
#     print(response.text)
# else:
#     # Save image
#     with open("generated_image.jpg", "wb") as f:
#         f.write(response.content)

#     print("✅ Image saved as generated_image.jpg")






import requests
import json

# 🔧 CONFIGURATION\

# glm-4.7-flash cloud flash
# WORKER_URL = "https://gklm47deploymentaiiglmodel.barisebot.workers.dev"  # Replace with your actual URL 
# API_KEY = "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"  # Replace with your actual API key


## qwen2.5-coder-32b-instruct 

# WORKER_URL = "https://qwenmodelllmcodingmodling.collegeaurora3.workers.dev"  
# API_KEY = "nvapiXr_OKhVXuXwag087vRAQBOnTz1udihnUoFpO7UcVCAyk3oeHiveVNIEjnWcGJRv"  ## qwen2.5-coder-32b-instruct

# gemma-3-12b-it

WORKER_URL = "http://gemmamodelforimageanddesigning.hiwings58.workers.dev"
API_KEY = "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"

def test_glm():
    """Test the GLM-4.7-Flash Worker"""
    print("=" * 60)
    print("Testing GLM-4.7-Flash Worker")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Simple greeting
    print("\n[Test 1] Simple greeting")
    print("-" * 60)
    payload = {"message": "Give me a complete html,css and js for creating a slide make sure i need only one slide called it as title and it should have a image and a text and a button"}
    response = requests.post(f"{WORKER_URL}/", headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Success!")
        print(f"Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
    
    # Test 2: Code generation
    print("\n[Test 2] Code generation")
    print("-" * 60)
    payload = {"message": "Write a Python function to calculate the area of a circle"}
    response = requests.post(f"{WORKER_URL}/", headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Success!")
        print(f"Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_glm()



import requests
import json
import time
import base64


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


