import os
from google import genai
from playwright.sync_api import sync_playwright

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPT = """
You are a QA testing agent.
Look at this webpage screenshot and identify the single best clickable element to test next.
Return ONLY the exact visible text of the clickable element.
If there is no clickable element, return NONE.
Do not include explanations.
"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto("https://example.com")
    page.screenshot(path="page_before.png")
    print("Initial screenshot captured")

    uploaded_file = client.files.upload(file="page_before.png")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[PROMPT, uploaded_file],
    )

    target_text = response.text.strip()
    print("\nAI selected element to click:\n")
    print(target_text)

    if target_text == "NONE":
        print("\nNo clickable element found. Stopping.")
    else:
        page.get_by_text(target_text, exact=False).first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="page_after.png")
        print("\nClicked element and saved page_after.png")

    browser.close()