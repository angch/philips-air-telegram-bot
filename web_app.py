import base64
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import logging
import asyncio

# Import logic from the bot
# We assume air_purifier_bot.py is in the same directory
from air_purifier_bot import get_air_purifier_status, generate_status_diagram

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        data = await get_air_purifier_status()
        if not data:
             return templates.TemplateResponse("index.html", {"request": request, "error": "Could not fetch status from device."})

        # Generate diagram
        image_data = await generate_status_diagram(data)
        image_b64 = None
        if image_data:
            image_b64 = base64.b64encode(image_data).decode('utf-8')

        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": data,
            "image_b64": image_b64
        })
    except Exception as e:
        logging.error(f"Error in web app: {e}")
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

@app.get("/mock", response_class=HTMLResponse)
async def read_mock(request: Request):
    try:
        mock_data = {
            'name': 'Mock Device',
            'type': 'AC1234',
            'pm25': 45,
            'iaql': 6,
            'fltsts1': 1000,
            'flttotal1': 4000,
            'fltsts0': 200,
            'flttotal0': 720,
            'err': 0
        }

        image_data = await generate_status_diagram(mock_data)
        image_b64 = None
        if image_data:
            image_b64 = base64.b64encode(image_data).decode('utf-8')

        return templates.TemplateResponse("index.html", {
            "request": request,
            "data": mock_data,
            "image_b64": image_b64
        })
    except Exception as e:
        logging.error(f"Error in web app: {e}")
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
