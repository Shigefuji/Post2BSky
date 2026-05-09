import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from Post2BSky import BlueSkyBot

# Secret から環境変数で credentials.json 内容を取得し、ファイルに書き込む
def setup_credentials():
    """Secret の credentials.json 内容を環境変数から /tmp に書き込む"""
    creds_json_str = os.environ.get('GSPREAD_CREDENTIALS')
    if creds_json_str:
        try:
            # 環境変数の JSON 文字列をパース
            creds_data = json.loads(creds_json_str)
            with open('/tmp/credentials.json', 'w') as f:
                json.dump(creds_data, f)
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/tmp/credentials.json'
        except Exception as e:
            print(f"Warning: Could not setup credentials from env var: {e}")
    elif os.path.exists('/secrets/credentials.json'):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/secrets/credentials.json'

setup_credentials()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        # For /health, just respond OK quickly without running the bot
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
            return

        try:
            config = {
                'username': os.environ.get('BSKY_USERNAME'),
                'password': os.environ.get('BSKY_PASSWORD'),
                'deepl_api_key': os.environ.get('DEEPL_API_KEY'),
                'gemini_api_key': os.environ.get('GEMINI_API_KEY'),
                'spreadsheet_key': os.environ.get('SPREADSHEET_KEY'),
            }
            missing = [k for k, v in config.items() if not v]
            if missing:
                raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

            bot = BlueSkyBot(config=config)
            bot.run()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8", "replace"))


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Listening on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
