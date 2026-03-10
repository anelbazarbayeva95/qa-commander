import os
from google import genai
from playwright.sync_api import sync_playwright

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPT_TEMPLATE = """
You are a QA testing agent.

Goal: explore the website by clicking one useful visible clickable element at a time.

Rules:
- Return ONLY the exact visible text of the single best clickable element to test next.
- Do not return anything already clicked before.
- If there is nothing useful to click, return NONE.
- Do not include explanations.

Already clicked:
{clicked_items}
"""

MAX_STEPS = 3
clicked_history = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto("https://example.com")

    for step in range(1, MAX_STEPS + 1):
        screenshot_name = f"step_{step}.png"
        page.screenshot(path=screenshot_name)
        print(f"\nStep {step}: screenshot saved as {screenshot_name}")

        uploaded_file = client.files.upload(file=screenshot_name)

        prompt = PROMPT_TEMPLATE.format(
            clicked_items=", ".join(clicked_history) if clicked_history else "None"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, uploaded_file],
        )

        target_text = response.text.strip()
        print(f"AI selected: {target_text}")

        if target_text == "NONE":
            print("No more useful clickable elements found. Stopping.")
            break

        try:
            page.get_by_text(target_text, exact=False).first.click()
            page.wait_for_timeout(2000)
            clicked_history.append(target_text)
            print(f"Clicked: {target_text}")
            print(f"Current URL: {page.url}")
        except Exception as e:
            print(f"Failed to click '{target_text}': {e}")
            break

    browser.close()

print("\nRun complete.")
print("Clicked history:", clicked_history)