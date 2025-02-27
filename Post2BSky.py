import datetime
import json
import urllib.request
import deepl
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import yfinance as yf
from pytrends.request import TrendReq
from atproto import Client
import feedparser

class BlueSkyBot:
    def __init__(self, config_file):
        """
        コンストラクタ：設定ファイルを読み込み、各APIの初期化を行います。

        Args:
            config_file (str): 設定ファイルのパス
        """
        with open(config_file, 'r') as file:
            self.config = json.load(file)
        self.api_client = Client(base_url='https://bsky.social')
        self.api_client.login(self.config['username'], self.config['password'])
        #self.trends_client = TrendReq(hl='ja-JP', tz=-540)
        self.translator = deepl.Translator(self.config['deepl_api_key'])
        genai.configure(api_key=self.config['gemini_api_key'])
        self.gemini_model = genai.GenerativeModel("gemini-1.5-flash") 
        """("gemini-pro")"""

    def connect_to_gspread(self):
        """
        Googleスプレッドシートに接続します。
        """
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.config['gspread_json_file'], scope)
        gspread_client = gspread.authorize(credentials)
        self.worksheet = gspread_client.open_by_key(self.config['spreadsheet_key']).worksheet('PostLog')

    def log_to_gspread(self, timestamp, message):
        """
        Googleスプレッドシートにログを記録します。

        Args:
            timestamp (str): 日時
            message (str): メッセージ

        Returns:
            int: 記録後の行数
        """
        self.worksheet.append_row([timestamp, message])
        return len(self.worksheet.col_values(1))

    def fetch_exchange_rate(self):
        """
        為替情報を取得します。

        Returns:
            str: 為替情報の文字列
        """
        ticker = yf.Ticker("USDJPY=X")
        history = ticker.history(period="1d")
    
        if not history.empty:
            open_price = round(history['Open'].iloc[0], 3)
            high_price = round(history['High'].iloc[0], 3)
            low_price = round(history['Low'].iloc[0], 3)
            close_price = round(history['Close'].iloc[0], 3)
        else:
            open_price = high_price = low_price = close_price = 'データなし'

        return f"為替情報\n始:{open_price}\n高:{high_price}\n安:{low_price}\n終:{close_price}\n"

    def fetch_weather(self):
        """
        天気情報を取得します。

        Returns:
            str: 天気情報の文字列
        """
        url = "https://www.jma.go.jp/bosai/forecast/data/forecast/300000.json"
        weather_data = urllib.request.urlopen(url).read()
        weather_info = json.loads(weather_data.decode("utf-8"))[0]["timeSeries"][0]["areas"][0]["weathers"][0]
        weather_info = weather_info.replace("\u3000", " ")
        return f'\n和歌山北部の天気: {weather_info}\n'

    def fetch_trending_keywords(self):
        """
        トレンド情報を取得します。

        Returns:
            str: トレンド情報の文字列
        """
        url = 'https://trends.google.com/trending/rss?geo=JP'
        feed = feedparser.parse(url)
        word = ""
        for entry in feed.entries:
            word += entry.title + "\n"
            #print(entry.title, entry.link)


        # trends_data = self.trends_client.trending_searches(pn='japan')
        #return f'\n\nトレンドワード\n{trends_data.head(10).values.flatten().tolist()}\n'
        return f'\n\nトレンドワード\n{word}\n'

    def fetch_japanese_quote(self):
        """
        日本語の名言を取得します。

        Returns:
            str: 日本語の名言の文字列
        """
        url = "https://meigen.doodlenote.net/api/json.php"
        quote_data = json.loads(urllib.request.urlopen(url).read())
        return f"{quote_data[0]['meigen']} by {quote_data[0]['auther']}"

    def translate_to_japanese(self, text):
        """
        英語のテキストを日本語に翻訳します。

        Args:
            text (str): 英語のテキスト

        Returns:
            str: 翻訳された日本語のテキスト
        """
        return str(self.translator.translate_text(text, source_lang='EN', target_lang='JA'))

    def fetch_english_quote(self):
        """
        英語の名言を取得し、日本語に翻訳します。

        Returns:
            str: 英語の名言とその翻訳の文字列
        """
        url = "https://zenquotes.io/api/today"
        quote_data = json.loads(urllib.request.urlopen(url).read())
        english_quote, author = quote_data[0]["q"], quote_data[0]["a"]
        translated_quote = self.translate_to_japanese(english_quote)
        translated_author = self.translate_to_japanese(author)
        return f'\n今日の英語名言:\n{english_quote} by {author}\n日本語訳:\n{translated_quote} 著者: {translated_author}\n'

    def generate_description(self, term, additional_instructions):
        """
        単語の解説を生成します。

        Args:
            term (str): 解説する単語
            additional_instructions (str): 追加の指示文

        Returns:
            str: 解説の文字列
        """
        prompt = f"{term}について500文字以内で説明してください。 {additional_instructions}"
        response = self.gemini_model.generate_content(prompt)
        return f"【{term} について】\n{response.text}\n"

    def post_to_bluesky(self, message):
        """
        BlueSkyに投稿します。

        Args:
            message (str): 投稿するメッセージ
        """
        for i in range(0, len(message), 300):
            partial_message = message[i:i + 300]
            self.api_client.send_post(partial_message)

    def run(self):
        """
        各種情報を取得し、ログを残してBlueSkyに投稿します。
        """
        self.connect_to_gspread()
        timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S") + '\n'
        weather_message = self.fetch_weather()
        exchange_rate_message = self.fetch_exchange_rate()
        english_quote_message = self.fetch_english_quote()
        trends_message = self.fetch_trending_keywords()
        
        # candidate.safety_ratings で不適切である場合はリトライ
        for _ in range(3):  
            try:
                japanese_quote_message = self.generate_description(self.fetch_japanese_quote(), "ポジティブな言葉で元気が出る解説をしてください。質問の言葉を解答から除いてください")
            except Exception as e:
                print("Retry:Generate description\n")
            else:
                break 
        else:
            japanese_quote_message = "今日は何もない日ですが、特別な一日です。元気を出して行きましょう！"
    
        for message in [weather_message, exchange_rate_message, english_quote_message, trends_message , japanese_quote_message]:
        #for message in [weather_message, exchange_rate_message, english_quote_message, japanese_quote_message]:
            print("Postlog No:", self.log_to_gspread(timestamp, message), "\n")
            self.post_to_bluesky(timestamp + message)

        #print(timestamp + weather_message + exchange_rate_message + english_quote_message + trends_message + japanese_quote_message)"""
        print(timestamp)
        print(weather_message)
        print(exchange_rate_message)
        print(english_quote_message)
        print(trends_message)
        print(japanese_quote_message)
        
if __name__ == "__main__":
    bot = BlueSkyBot('.env.local')
    bot.run()
