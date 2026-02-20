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
        # 利用可能なモデルをリストして、利用可能なモデル名を選ぶ
        try:
            available_models = genai.list_models()
        except Exception:
            available_models = None

        chosen_model_name = None
        if available_models:
            # available_models の各要素の形状は環境により異なる（dict またはオブジェクト）ため
            # 柔軟に name を取り出す
            for m in available_models:
                name = None
                if isinstance(m, dict):
                    name = m.get('name') or m.get('model')
                else:
                    name = getattr(m, 'name', None) or getattr(m, 'model', None)
                if not name:
                    continue
                # 'gemini' を含むモデルを優先して選択
                if 'gemini' in name:
                    chosen_model_name = name
                    break
            # なければ最初のモデルを候補とする
            if chosen_model_name is None and len(available_models) > 0:
                m = available_models[0]
                if isinstance(m, dict):
                    chosen_model_name = m.get('name') or m.get('model')
                else:
                    chosen_model_name = getattr(m, 'name', None) or getattr(m, 'model', None)

        # デフォルトのハードコードを置いておきつつ、上で見つかったら置き換える
        default_model = "gemini-1.5-flash"
        model_to_use = chosen_model_name or default_model
        try:
            self.gemini_model = genai.GenerativeModel(model_to_use)
        except Exception as e:
            # 最後の手段として None にしておき、呼び出し側で再試行ロジックを動かす
            print("Warning: could not initialize GenerativeModel with", model_to_use, e)
            self.gemini_model = None

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

        try:
            # weather_data は生のJSONバイト列なので、人が読む説明を作る際は
            # 既に整形した weather_info（文字列）を渡す方が安全です。
            japanese_weather_message = self.generate_description(
                weather_info,
                "あなたはわかりやすい解説で有名な天気予報士です、このJSONデータをもとに、今日の天気をできるだけ詳しく150文字以内で説明してください、データについての説明や、データの内容を回答にふくめないでください"
            )
        except Exception as e:
            # 生成に失敗した場合は例外内容をログに出し、フォールバックの文言を設定する
            print("Retry:Generate description\n", e)
            japanese_weather_message = "天気情報の要約を生成できませんでした。"

        return f"\n和歌山北部の天気: {japanese_weather_message}\n"

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
        prompt = f"{term} {additional_instructions}"
        # self.gemini_model が None の場合や generate_content が失敗した場合に備えて
        # 再試行とフォールバックを実装する
        last_exception = None
        # 優先: 現在のモデル、次に list_models() で見つけた候補
        candidates = []
        if self.gemini_model is not None:
            candidates.append(self.gemini_model)

        try:
            models = genai.list_models()
            for m in models:
                name = None
                if isinstance(m, dict):
                    name = m.get('name') or m.get('model')
                else:
                    name = getattr(m, 'name', None) or getattr(m, 'model', None)
                if not name:
                    continue
                try:
                    candidates.append(genai.GenerativeModel(name))
                except Exception:
                    continue
        except Exception:
            # list_models が失敗しても実行は継続
            pass

        import time
        for candidate in candidates:
            # 簡易的にモデル名に 'embed' や 'embedding' を含むものはスキップ（generate_content をサポートしない可能性が高い）
            try:
                model_name = None
                if hasattr(candidate, 'model'):
                    model_name = getattr(candidate, 'model')
                elif hasattr(candidate, 'name'):
                    model_name = getattr(candidate, 'name')
                elif hasattr(candidate, '__class__'):
                    model_name = str(candidate)
                if model_name and ('embed' in model_name.lower() or 'embedding' in model_name.lower()):
                    print("Skipping embedding model candidate:", model_name)
                    continue
            except Exception:
                # 名前の取得に失敗しても試行は続ける
                pass

            # 429 などの一時的エラーにはバックオフして複数回リトライ
            attempt = 0
            max_attempts = 3
            backoff = 1.0
            while attempt < max_attempts:
                try:
                    response = candidate.generate_content(prompt)
                    return f"{response.text}\n"
                except Exception as e:
                    last_exception = e
                    msg = str(e)
                    # 429 の場合は待って再試行
                    if '429' in msg or 'quota' in msg.lower():
                        wait = backoff
                        print(f"Quota/error from model, backing off {wait}s and retrying... ({attempt+1}/{max_attempts})")
                        time.sleep(wait)
                        backoff *= 2
                        attempt += 1
                        continue
                    else:
                        print("generate_content failed for candidate, trying next:", e)
                        break

        # ここまで到達したら全て失敗 -> 安全なフォールバックメッセージを返す
        print("All model attempts failed. Returning fallback message.")
        return "天気情報の要約を生成できませんでした。しばらくしてから再度お試しください。\n"

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
        # exchange_rate_message = self.fetch_exchange_rate() APIが安定しないため当面コメントアウト
        english_quote_message = self.fetch_english_quote()
        trends_message = self.fetch_trending_keywords()
        
        # candidate.safety_ratings で不適切である場合はリトライ
        for _ in range(3):  
            try:
                japanese_quote_message = self.generate_description(self.fetch_japanese_quote(), "質問の言葉を含めて150文字以内でポジティブな言葉で元気が出る解説をしてください。")
            except Exception as e:
                print("Retry:Generate description\n")
            else:
                break 
        else:
            japanese_quote_message = "今日は何もない日ですが、特別な一日です。元気を出して行きましょう！"

        for message in [weather_message, english_quote_message, trends_message , japanese_quote_message]:    
        #for message in [weather_message, exchange_rate_message, english_quote_message, trends_message , japanese_quote_message]:
        #for message in [weather_message, exchange_rate_message, english_quote_message, japanese_quote_message]:
            print("Postlog No:", self.log_to_gspread(timestamp, message), "\n")
            self.post_to_bluesky(timestamp + message)

        #print(timestamp + weather_message + exchange_rate_message + english_quote_message + trends_message + japanese_quote_message)"""
        print(timestamp)
        print(weather_message)
        # print(exchange_rate_message)
        print(english_quote_message)
        print(trends_message)
        print(japanese_quote_message)
        
if __name__ == "__main__":
    bot = BlueSkyBot('.env.local')
    bot.run()
