import asyncio
import os
import logging
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

# Setup Jinja2 environment
TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

async def render_status_image(data):
    """
    Renders the status data into an image using HTML template and Playwright.
    """
    try:
        # Prepare data for template
        pm25 = data.get('pm25', 0)

        # Calculate PM2.5 color and gauge percent (assuming max 200 for gauge full)
        pm25_percent = min((pm25 / 200) * 100, 100)
        if pm25 < 12:
            pm25_color = "var(--good-color)"
            iaql_text = "Good"
        elif pm25 < 35:
            pm25_color = "var(--fair-color)"
            iaql_text = "Fair"
        elif pm25 < 55:
            pm25_color = "var(--poor-color)"
            iaql_text = "Poor"
        else:
            pm25_color = "var(--bad-color)"
            iaql_text = "Bad"

        # Filters
        filters = []
        # Main Filter (Index 1)
        total1 = data.get('flttotal1', 1)
        curr1 = data.get('fltsts1', 0)
        pct1 = int((curr1 / total1) * 100) if total1 > 0 else 0
        filters.append({
            "name": "Main Filter",
            "percent": pct1,
            "color": "var(--good-color)" if pct1 > 20 else "var(--bad-color)"
        })

        # Pre Filter (Index 0)
        total0 = data.get('flttotal0', 1)
        curr0 = data.get('fltsts0', 0)
        pct0 = int((curr0 / total0) * 100) if total0 > 0 else 0
        filters.append({
            "name": "Pre-Filter",
            "percent": pct0,
            "color": "var(--good-color)" if pct0 > 20 else "var(--bad-color)"
        })

        template_data = {
            "name": data.get('name', 'Air Purifier'),
            "pm25": pm25,
            "pm25_percent": pm25_percent,
            "pm25_color": pm25_color,
            "iaql": data.get('iaql', '-'),
            "iaql_text": iaql_text,
            "filters": filters,
            "err": data.get('err', 0)
        }

        # Render HTML
        template = env.get_template('status_template.html')
        html_content = template.render(**template_data)

        # Generate Image with Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Set viewport size to ensure container fits
            await page.set_viewport_size({"width": 500, "height": 600})

            await page.set_content(html_content)

            # Locate the container and screenshot it
            # We wait for the container to be visible
            locator = page.locator('.container')
            await locator.wait_for()

            screenshot_bytes = await locator.screenshot()

            await browser.close()

            return screenshot_bytes

    except Exception as e:
        logging.error(f"Error rendering status image: {e}")
        return None
