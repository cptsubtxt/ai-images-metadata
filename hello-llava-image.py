import ollama

response = ollama.chat(
    model="llava",
    messages=[
        {"role": "user", 
         "content": "Your are a photo journalist, describe the image", 
         "images": ["test-image.jpg"]}
    ],
)

print(response["message"]['role'])
print(response["message"]['content'])