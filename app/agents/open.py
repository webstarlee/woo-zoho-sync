from openai import OpenAI
from app.config import settings

class OpenAgent:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def get_completion(self, text):
        prompt = f"""
            Translate the following text to English: {text}
            Need to return only plain text, no markdown or other formatting.
        """
        result = self.client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        return result.choices[0].message.content