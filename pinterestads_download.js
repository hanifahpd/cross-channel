const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

// --- Settings ---
const BASE_DIR = "A:path/to/directory";
const URL_FILE_PATH = path.join(BASE_DIR, "url.txt");
// const DOWNLOAD_DIR = BASE_DIR;
const TARGET_STRING = "Name%20of%20your%20string";
const DOWNLOAD_FILENAME = path.join(BASE_DIR, "Saved filename.csv");

async function main() {
    let browser;
    try {
        // 1. Read URL from file
        if (!fs.existsSync(URL_FILE_PATH)) {
            console.log(`File ${URL_FILE_PATH} not found.`);
            return;
        }

        const startUrl = fs.readFileSync(URL_FILE_PATH, 'utf8').trim();
        if (!startUrl || !startUrl.startsWith('http')) {
            console.log(`Invalid URL in file: ${startUrl}`);
            return;
        }

        console.log(`Read URL: ${startUrl}`);

        // 2. Setup Playwright
        console.log("Setting up browser...");
        browser = await chromium.launch({ headless: false }); // Set true for headless
        const context = await browser.newContext();
        const page = await context.newPage();

        // 3. Set up the Network Listener (the magic part)
        // Start listening BEFORE loading the page
        console.log(`Waiting for network request containing '${TARGET_STRING}'...`);
        const requestPromise = page.waitForRequest(url => 
            url.url().includes(TARGET_STRING)
        );

        // 4. Load Page
        console.log(`Loading page: ${startUrl}...`);
        await page.goto(startUrl, { waitUntil: 'networkidle' });

        // 5. Find and Click the Button
        const buttonLocator = page.locator('[data-test-id="scheduledEmailDownloadButton"]');
        console.log("Looking for button...");
        await buttonLocator.waitFor({ state: 'visible', timeout: 20000 });
        
        console.log("Button found. Clicking button...");
        await buttonLocator.click();

        // 6. Wait for the listener to find the request
        const request = await requestPromise;
        const foundUrl = request.url();

        console.log(`\n--- SUCCESS! Intercepted Download URL ---`);
        console.log(foundUrl);
        console.log("------------------------------------------\n");

        // 7. Download the file using Playwright's built-in 'request'
        // This automatically uses the browser's cookies and auth state
        console.log("Downloading file using the intercepted URL...");
        
        // 'page.request' acts like a separate 'fetch' or 'axios'
        // that shares the browser's cookies
        const response = await page.request.get(foundUrl);

        if (!response.ok()) {
            throw new Error(`Download failed with status: ${response.status()}`);
        }

        // Get the file content
        const buffer = await response.body();

        // Save the file
        const downloadPath = path.join(DOWNLOAD_FILENAME);
        fs.writeFileSync(downloadPath, buffer);

        console.log(`File downloaded successfully and saved to:`);
        console.log(downloadPath);

    } catch (error) {
        console.error(`\nAn error occurred: ${error}`);
    } finally {
        if (browser) {
            console.log("Closing browser.");
            await browser.close();
        }
    }
}

main();
