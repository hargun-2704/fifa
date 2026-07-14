from google import genai
client = genai.Client(api_key="AQ.Ab8RN6J12AcUBm66w1L2HJd5niFfv1S4LMhsi-XO5m8BBCfPTg")
r = client.models.generate_content(model="gemini-3-flash-preview", contents="Say hello in one word")
print(r.text)