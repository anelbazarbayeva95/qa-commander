import os
from google import genai
from playwright.sync_api import sync_playwright

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Step 1 — open browser
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto("https://example.com")

    # Step 2 — take screenshot
    page.screenshot(path="page.png")

    print("Screenshot captured")

    browser.close()

# Step 3 — upload screenshot to Gemini
uploaded_file = client.files.upload(file="page.png")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        """
You are a QA testing agent.
Look at this webpage screenshot and list any clickable elements like buttons or links.
Return ONLY the clickable element names.
One per line.
Do not include explanations.
""",
        uploaded_file,
    ],
)

print("\nAI detected clickable elements:\n")
print(response.text)