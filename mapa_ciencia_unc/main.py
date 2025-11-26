from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hello World</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                background-color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-family: Arial, sans-serif;
            }
        </style>
    </head>
    <body>
        <h1>hello world</h1>
    </body>
    </html>
    """
