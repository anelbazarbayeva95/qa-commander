import json
import os
from urllib.parse import urlparse
from datetime import datetime
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

BUG_REPORT_PROMPT_TEMPLATE = """
You are an AI QA analyst.

Based on this step data, produce a concise QA bug summary.

Step: {step}
Before URL: {before_url}
After URL: {after_url}
Selected element: {selected_element}
Status: {status}
Visual flags: {visual_flags}
Console errors: {console_errors}
Network failures: {network_failures}

Return exactly this structure:
ISSUE_TITLE: one short line
SEVERITY: LOW, MEDIUM, or HIGH
EXPECTED_RESULT: one sentence
ACTUAL_RESULT: one sentence
LIKELY_CAUSE: one sentence
"""

MAX_STEPS = int(os.environ.get("MAX_STEPS", "3"))
clicked_history = []
run_log = []

ALLOWED_ORIGINS = {
    "example.com",
    "www.iana.org",
    "datatracker.ietf.org",
}
console_events = []
network_failures = []

run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
run_screenshot_dir = f"screenshots/run_{run_id}"
reports_dir = "reports"

os.makedirs(run_screenshot_dir, exist_ok=True)
os.makedirs(reports_dir, exist_ok=True)


def summarize_step_status(step_entry):
    if "error" in step_entry:
        return "FAIL"
    if step_entry["network_failures"]:
        return "WARNING"
    if step_entry["console_errors"]:
        return "WARNING"
    if step_entry["selected_element"] == "NONE":
        return "STOPPED"
    return "PASS"


def safe_generate_content(prompt_text):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
        )
        return response.text.strip()
    except Exception as e:
        return (
            "ISSUE_TITLE: Bug summary unavailable\n"
            "SEVERITY: LOW\n"
            "EXPECTED_RESULT: The step should be summarized successfully.\n"
            "ACTUAL_RESULT: Gemini could not generate the bug summary.\n"
            f"LIKELY_CAUSE: {str(e)}"
        )


def parse_bug_report(text):
    result = {
        "issue_title": "No issue detected",
        "severity": "LOW",
        "expected_result": "The page should load and behave normally.",
        "actual_result": "The page loaded without critical issues.",
        "likely_cause": "No obvious issue detected.",
    }

    for line in text.splitlines():
        if line.startswith("ISSUE_TITLE:"):
            result["issue_title"] = line.replace("ISSUE_TITLE:", "").strip()
        elif line.startswith("SEVERITY:"):
            result["severity"] = line.replace("SEVERITY:", "").strip()
        elif line.startswith("EXPECTED_RESULT:"):
            result["expected_result"] = line.replace("EXPECTED_RESULT:", "").strip()
        elif line.startswith("ACTUAL_RESULT:"):
            result["actual_result"] = line.replace("ACTUAL_RESULT:", "").strip()
        elif line.startswith("LIKELY_CAUSE:"):
            result["likely_cause"] = line.replace("LIKELY_CAUSE:", "").strip()

    return result


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    def handle_console(msg):
        entry = {
            "type": msg.type,
            "text": msg.text,
            "location": msg.location,
            "page_url": page.url,
        }
        console_events.append(entry)

    def handle_request_failed(request):
        failure = request.failure
        entry = {
            "url": request.url,
            "method": request.method,
            "failure_text": failure.get("errorText") if failure else "Unknown failure",
            "page_url": page.url,
        }
        network_failures.append(entry)

    page.on("console", handle_console)
    page.on("requestfailed", handle_request_failed)

    start_url = os.environ.get("TARGET_URL", "https://example.com")
    if not start_url.startswith(("http://", "https://")):
        start_url = "https://" + start_url
    page.goto(start_url)

    for step in range(1, MAX_STEPS + 1):
        console_start_index = len(console_events)
        network_start_index = len(network_failures)

        screenshot_name = f"{run_screenshot_dir}/step_{step}.png"
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

        step_entry = {
            "step": step,
            "before_url": page.url,
            "selected_element": target_text,
            "screenshot": screenshot_name,
            "status": "UNKNOWN",
            "after_url": page.url,
            "console_errors": [],
            "network_failures": [],
            "visual_flags": [],
            "issue_title": "No issue detected",
            "severity": "LOW",
            "expected_result": "The selected page should load correctly after the click.",
            "actual_result": "No critical issue detected.",
            "likely_cause": "No obvious issue detected.",
        }

        if target_text == "NONE":
            step_entry["visual_flags"].append("No additional useful clickable elements found.")
            step_entry["status"] = "STOPPED"
            run_log.append(step_entry)
            break

        try:
            clicked = False

            # Try clicking a link first
            try:
                locator = page.get_by_role("link", name=target_text)
                locator.first.scroll_into_view_if_needed()
                locator.first.click(timeout=5000)
                clicked = True
            except Exception:
                pass

            # Try clicking a button
            if not clicked:
                try:
                    locator = page.get_by_role("button", name=target_text)
                    locator.first.scroll_into_view_if_needed()
                    locator.first.click(timeout=5000)
                    clicked = True
                except Exception:
                    pass

            # Fallback to text
            if not clicked:
                try:
                    locator = page.get_by_text(target_text, exact=False)
                    locator.first.scroll_into_view_if_needed()
                    locator.first.click(timeout=5000)
                    clicked = True
                except Exception:
                    pass

            if not clicked:
                raise Exception(f"Could not click element: {target_text}")

            page.wait_for_timeout(2000)

            clicked_history.append(target_text)
            step_entry["after_url"] = page.url
            print(f"Clicked: {target_text}")
            print(f"Current URL: {page.url}")

            if page.url == step_entry["before_url"]:
                step_entry["visual_flags"].append("URL did not change after click.")

            current_origin = urlparse(page.url).netloc
            if current_origin and current_origin not in ALLOWED_ORIGINS:
                step_entry["visual_flags"].append(
                    f"Navigated outside allowed origins: {current_origin}"
                )
        except Exception as e:
            step_entry["status"] = "FAIL"
            step_entry["error"] = str(e)
            step_entry["visual_flags"].append("Playwright could not click the selected element.")
            print(f"Failed to click '{target_text}': {e}")
            run_log.append(step_entry)
            break

        step_console_events = console_events[console_start_index:]
        step_network_failures = network_failures[network_start_index:]

        step_entry["console_errors"] = [
            event for event in step_console_events if event["type"] == "error"
        ]
        step_entry["network_failures"] = step_network_failures

        if step_entry["console_errors"]:
            step_entry["visual_flags"].append("Console errors detected after navigation.")
        if step_entry["network_failures"]:
            step_entry["visual_flags"].append("Failed network requests detected after navigation.")

        step_entry["status"] = summarize_step_status(step_entry)

        bug_prompt = BUG_REPORT_PROMPT_TEMPLATE.format(
            step=step_entry["step"],
            before_url=step_entry["before_url"],
            after_url=step_entry["after_url"],
            selected_element=step_entry["selected_element"],
            status=step_entry["status"],
            visual_flags=step_entry["visual_flags"] if step_entry["visual_flags"] else "None",
            console_errors=[event["text"] for event in step_entry["console_errors"]] if step_entry["console_errors"] else "None",
            network_failures=[failure["failure_text"] for failure in step_entry["network_failures"]] if step_entry["network_failures"] else "None",
        )
        bug_report_text = safe_generate_content(bug_prompt)
        bug_report = parse_bug_report(bug_report_text)
        step_entry.update(bug_report)

        run_log.append(step_entry)

    browser.close()

json_report_path = f"{reports_dir}/run_{run_id}.json"
md_report_path = f"{reports_dir}/run_{run_id}.md"

summary = {
    "total_steps_completed": len(run_log),
    "pass_count": sum(1 for entry in run_log if entry["status"] == "PASS"),
    "warning_count": sum(1 for entry in run_log if entry["status"] == "WARNING"),
    "fail_count": sum(1 for entry in run_log if entry["status"] == "FAIL"),
    "stopped_count": sum(1 for entry in run_log if entry["status"] == "STOPPED"),
}

json_report = {
    "run_id": run_id,
    "start_url": start_url,
    "max_steps": MAX_STEPS,
    "clicked_history": clicked_history,
    "steps": run_log,
    "console_event_count": len(console_events),
    "network_failure_count": len(network_failures),
    "summary": summary,
}

with open(json_report_path, "w", encoding="utf-8") as f:
    json.dump(json_report, f, indent=2)

with open(md_report_path, "w", encoding="utf-8") as f:
    f.write(f"# QA Commander Report — {run_id}\n\n")
    f.write(f"- Start URL: {start_url}\n")
    f.write(f"- Max steps: {MAX_STEPS}\n")
    f.write(f"- Clicked history: {', '.join(clicked_history) if clicked_history else 'None'}\n\n")
    f.write(f"- Console event count: {len(console_events)}\n")
    f.write(f"- Network failure count: {len(network_failures)}\n\n")

    f.write("## Test Summary\n\n")
    f.write(f"- Total steps completed: {summary['total_steps_completed']}\n")
    f.write(f"- Passed: {summary['pass_count']}\n")
    f.write(f"- Warnings: {summary['warning_count']}\n")
    f.write(f"- Failures: {summary['fail_count']}\n")
    f.write(f"- Stopped: {summary['stopped_count']}\n\n")

    f.write("## Steps\n\n")

    if run_log:
        for entry in run_log:
            f.write(f"### Step {entry['step']}\n")
            f.write(f"- Before URL: {entry['before_url']}\n")
            f.write(f"- Selected element: {entry['selected_element']}\n")
            f.write(f"- Status: {entry['status']}\n")
            f.write(f"- After URL: {entry['after_url']}\n")
            f.write(f"- Screenshot: {entry['screenshot']}\n")
            f.write(f"- Console errors: {len(entry['console_errors'])}\n")
            f.write(f"- Network failures: {len(entry['network_failures'])}\n")
            f.write(f"- Issue title: {entry['issue_title']}\n")
            f.write(f"- Severity: {entry['severity']}\n")
            f.write(f"- Expected result: {entry['expected_result']}\n")
            f.write(f"- Actual result: {entry['actual_result']}\n")
            f.write(f"- Likely cause: {entry['likely_cause']}\n")
            if entry['visual_flags']:
                f.write("- Visual flags:\n")
                for flag in entry['visual_flags']:
                    f.write(f"  - {flag}\n")
            if entry['console_errors']:
                f.write("- Console error details:\n")
                for event in entry['console_errors']:
                    f.write(f"  - {event['text']}\n")
            if entry['network_failures']:
                f.write("- Network failure details:\n")
                for failure in entry['network_failures']:
                    f.write(f"  - {failure['method']} {failure['url']} → {failure['failure_text']}\n")
            if "error" in entry:
                f.write(f"- Error: {entry['error']}\n")
            f.write("\n")
    else:
        f.write("No steps were completed.\n")

print("\nRun complete.")
print("Clicked history:", clicked_history)
print(f"JSON report saved: {json_report_path}")
print(f"Markdown report saved: {md_report_path}")