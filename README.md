
# Post2BSky

## Overview
Post2BSky is a Python program that fetches exchange rate information, weather information, trending words, quotes, and more, logs this information, and posts it to BlueSky. This bot uses various APIs to gather information and logs the information to a Google Spreadsheet.

## Required Libraries
To run this program, you will need the following Python libraries:

- `datetime`
- `json`
- `urllib.request`
- `deepl`
- `gspread`
- `oauth2client`
- `google.generativeai`
- `yfinance`
- `pytrends`
- `atproto`

You can install the required libraries using the following command:

```sh
pip install datetime json urllib.request deepl gspread oauth2client google-generativeai yfinance pytrends atproto
```

## Configuration File
A configuration file named `.env.local` is required. This file contains authentication information for various APIs. An example file is shown below:

```json
{
    "username": "your_bluesky_username",
    "password": "your_bluesky_password",
    "deepl_api_key": "your_deepl_api_key",
    "gemini_api_key": "your_gemini_api_key",
    "gspread_json_file": "your_gspread_json_file",
    "spreadsheet_key": "your_spreadsheet_key"
}
```

## Code Explanation

### Post2BSky Class
This class encapsulates all the functionalities of Post2BSky.

#### `__init__(self, config_file)`
Constructor. Loads the configuration file and initializes the APIs.

#### `connect_to_gspread(self)`
Connects to Google Spreadsheet.

#### `log_to_gspread(self, timestamp, message)`
Logs information to Google Spreadsheet.

#### `fetch_exchange_rate(self)`
Fetches exchange rate information.

#### `fetch_weather(self)`
Fetches weather information.

#### `fetch_trending_keywords(self)`
Fetches trending keywords.

#### `fetch_japanese_quote(self)`
Fetches a Japanese quote.

#### `translate_to_japanese(self, text)`
Translates English text to Japanese.

#### `fetch_english_quote(self)`
Fetches an English quote and translates it to Japanese.

#### `generate_description(self, term, additional_instructions)`
Generates a description of a specified term.

#### `post_to_bluesky(self, message)`
Posts a message to BlueSky.

#### `run(self)`
Fetches various information, logs it, and posts it to BlueSky.

## How to Run
1. Install the required libraries.
2. Create the `secret.json` file and input the appropriate authentication information.
3. Run the script as shown below:

```sh
python post2bsky.py
```

## Usage Example
Below is an example of how to use the Post2BSky class.

```python
if __name__ == "__main__":
    bot = Post2BSky('.env.local')
    bot.run()
```

This script uses the specified authentication information to fetch various information and post it to BlueSky. The fetched information is also logged to a Google Spreadsheet.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
