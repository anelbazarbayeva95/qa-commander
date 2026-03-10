import os
from google import genai
from playwright.sync_api import sync_playwright

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Step 1 — open browser and take screenshot
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    page.goto("https://example.com")

    page.screenshot(path="page.png")

    browser.close()

print("Screenshot captured")

# Step 2 — upload screenshot to Gemini and ask for analysis
uploaded_file = client.files.upload(file="page.png")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        "Describe what UI elements you see on this webpage.",
        uploaded_file,
    ],
)

print("\nGemini analysis:\n")
print(response.text)