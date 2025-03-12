import ollama

response = ollama.chat(
    model="llava",
    messages=[
        {"role": "user", 
         "content": "Your role is a newspaper editor. Describe the subject of the image in a headline with less than 8 words.", 
         "images": ["./FFCggEmmendingen.jpeg"]}
    ],
)

print(response["message"]['role'])
print(response["message"]['content'])