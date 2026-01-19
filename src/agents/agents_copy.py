import os
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI

print(find_dotenv())
print(load_dotenv(find_dotenv()))


#Get environment variables
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

model = ChatOpenAI(api_key=openrouter_api_key,
                   openai)