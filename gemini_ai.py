import os
import google.generativeai as genai
from datetime import datetime

class GeminiAI:
    def __init__(self, api_key, persona_prompt):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')
        self.persona_prompt = persona_prompt

    def generate_response(self, user_message, context_data=None):
        try:
            prompt = f"{self.persona_prompt}\n\nContext Data: {context_data}\n\nUser: {user_message}\nArcaina:"
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini Error: {e}")
            return "Maaf Master, sepertinya sistem AI saya sedang mengalami gangguan sinkronisasi. Sampaikan lagi perintah Anda."

    def get_daily_quest(self, context_data=None):
        prompt = f"{self.persona_prompt}\n\nContext Data: {context_data}\n\nBuatlah satu quest harian yang menantang tapi seru untuk membantu saya berkembang di dunia nyata hari ini. Singkat saja."
        response = self.model.generate_content(prompt)
        return response.text

    def get_level_up_praise(self, level, context_data=None):
        prompt = f"{self.persona_prompt}\n\nContext Data: {context_data}\n\nSaya baru saja naik ke level {level}! Tolong puji saya dengan gaya bicaramu yang keren."
        response = self.model.generate_content(prompt)
        return response.text
