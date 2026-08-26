'''
campaign and ad reporting from Pinterest Ads' site from gmail
is automatically downloaded by this python. Log in is required for the first-time access
'''

import asyncio
import os
from playwright.async_api import async_playwright

# --- Settings ---
BASE_DIR = r"A:path/to/directory"
URL_FILE_PATH = os.path.join(BASE_DIR, "url.txt")
DOWNLOAD_DIR = BASE_DIR
TARGET_STRING = "Cross%20channel%202026" #based on the file set on pinterest Ad Reporting
DOWNLOAD_FILENAME = "Cross channel 2026.csv" #set on pinterest ads site


async def main():
    # 1. Read URL from file
    if not os.path.exists(URL_FILE_PATH):
        print(f"File {URL_FILE_PATH} not found.")
        return

    with open(URL_FILE_PATH, "r", encoding="utf-8") as f:
        start_url = f.read().strip()

    if not start_url or not start_url.startswith("http"):
        print(f"Invalid URL in file: {start_url}")
        return

    print(f"Read URL: {start_url}")

    # 2. Launch browser
    print("Setting up browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # change to True for silent mode
        context = await browser.new_context()
        page = await context.new_page()

        # 3. Set up network listener before navigation
        print(f"Waiting for network request containing '{TARGET_STRING}'...")

        async def wait_for_request():
            return await page.wait_for_event(
                "request",
                predicate=lambda req: TARGET_STRING in req.url
            )

        request_task = asyncio.create_task(wait_for_request())

        # 4. Load the page
        print(f"Loading page: {start_url}...")
        await page.goto(start_url, wait_until="networkidle")

        # 5. Find and click the button
        print("Looking for download button...")
        button = page.locator('[data-test-id="scheduledEmailDownloadButton"]')
        await button.wait_for(state="visible", timeout=20000)
        print("Button found. Clicking button...")
        await button.click()

        # 6. Wait for the intercepted request
        request = await request_task
        found_url = request.url
        print("\n--- SUCCESS! Intercepted Download URL ---")
        print(found_url)
        print("------------------------------------------\n")

        # 7. Download the file using the same context
        print("Downloading file using the intercepted URL...")
        response = await context.request.get(found_url)

        if not response.ok:
            raise Exception(f"Download failed with status: {response.status}")

        download_path = os.path.join(DOWNLOAD_DIR, DOWNLOAD_FILENAME)
        with open(download_path, "wb") as f:
            f.write(await response.body())

        print(f"File downloaded successfully and saved to:\n{download_path}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
