import datetime
import os
import requests
from bs4 import BeautifulSoup
import tweepy

# ==== X(Twitter) API認証 ====
def create_twitter_client():
    api_key = os.environ["X_API_KEY"]
    api_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_secret = os.environ["X_ACCESS_SECRET"]

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    return tweepy.API(auth)

# ==== 天気情報を取得する関数（気象庁API版） ====
def get_weather_info():
    """気象庁APIを使用して福知山の天気情報を取得"""
    try:
        # 福知山市は京都府なので、京都府の天気予報を取得
        # 260000 = 京都府のエリアコード
        url = "https://www.jma.go.jp/bosai/forecast/data/forecast/260000.json"
        
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # 今日の天気データを取得
        today_weather = data[0]['timeSeries'][0]['areas'][0]
        
        # 気温データを取得（時系列データから）
        temp_data = None
        if len(data[0]['timeSeries']) > 2:
            temp_data = data[0]['timeSeries'][2]['areas'][0]
        
        weather = {
            "description": today_weather['weathers'][0],
            "temp": temp_data['temps'][0] if temp_data and temp_data['temps'] else "不明",
            "wind": today_weather['winds'][0] if today_weather['winds'] else "不明",
            "area": today_weather['area']['name']
        }
        
        return weather
        
    except Exception as e:
        print(f"⚠️ 天気情報の取得に失敗: {e}")
        return None

# ==== 天気情報を投稿用テキストに整形 ====
def format_weather_text(weather):
    """天気情報をX投稿用のテキストに整形"""
    if not weather:
        return "🌤️ 福知山市の天気情報を取得できませんでした"
    
    # 天気アイコンを選択
    weather_icon = "☀️"
    desc = weather["description"]
    if "雨" in desc:
        weather_icon = "🌧️"
    elif "雪" in desc:
        weather_icon = "❄️"
    elif "曇" in desc:
        weather_icon = "☁️"
    elif "霧" in desc:
        weather_icon = "🌫️"
    
    text = f"{weather_icon} 福知山市の天気\n"
    text += f"天気: {weather['description']}\n"
    if weather['temp'] != "不明":
        text += f"気温: {weather['temp']}°C\n"
    if weather['wind'] != "不明":
        text += f"風: {weather['wind']}\n"
    text += f"予報エリア: {weather['area']}"
    
    return text

# ==== イベントをXに投稿する関数 ====
def post_to_x(text, client):
    try:
        client.update_status(status=text)
        print("✅ 投稿完了: ", text[:30], "...")
    except Exception as e:
        print("⚠️ 投稿エラー:", e)

# ==== メイン処理 ====
def main():
    # Twitterクライアントを作成
    x_client = create_twitter_client()
    
    # 今日の天気情報を投稿
    weather = get_weather_info()
    weather_text = format_weather_text(weather)
    post_to_x(weather_text, x_client)
    
    # ==== イベント収集 ====
    today = datetime.date.today()
    url = f"https://www.city.fukuchiyama.lg.jp/calendar/index.php?dsp=1&y={today.year}&m={today.month}&d={today.day}"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, "html.parser")
    
    today_day_elem = soup.select_one(f'.t_day span:-soup-contains("{today.day}")')
    if not today_day_elem:
        print("今日の日付が見つかりませんでした")
        return
    
    today_calendar_day = today_day_elem.find_parent("dl", class_="calendar_day")
    if not today_calendar_day:
        print("今日のカレンダー要素が見つかりませんでした")
        return
    
    events = today_calendar_day.select(".cal_event_box")
    print(f"今日({today.month}月{today.day}日)のイベント数: {len(events)}")
    
    if len(events) == 0:
        # イベントがない場合は天気情報のみ投稿済み
        no_events_text = f"📅 {today.month}月{today.day}日の福知山市\n今日は特別なイベントはありません。\n素敵な一日をお過ごしください！"
        post_to_x(no_events_text, x_client)
        return
    
    # イベントごとに投稿
    for i, event in enumerate(events, 1):
        title_elem = event.select_one(".article_title a")
        title = title_elem.text.strip() if title_elem else "タイトル不明"
        
        category_elem = event.select_one(".cal_event_icon span")
        category = category_elem.text.strip() if category_elem else ""
        
        comment_elem = event.select_one(".cal_event_comment")
        comment = comment_elem.text.strip() if comment_elem else ""
        
        time_dt = event.select_one('dt:has(img[alt="開催時間"])')
        time = time_dt.find_next_sibling('dd').text.strip() if time_dt and time_dt.find_next_sibling('dd') else ""
        
        place_dt = event.select_one('dt:has(img[alt="開催場所"])')
        place = place_dt.find_next_sibling('dd').text.strip() if place_dt and place_dt.find_next_sibling('dd') else ""
        
        contact_dt = event.select_one('dt:has(img[alt="お問い合わせ"])')
        contact = contact_dt.find_next_sibling('dd').text.strip() if contact_dt and contact_dt.find_next_sibling('dd') else ""
        
        # 出力内容を整形
        text = f"📅 {title}"
        if len(events) > 1:
            text += f" ({i}/{len(events)})"
        text += "\n"
        
        if category:
            text += f"カテゴリ: {category}\n"
        if comment:
            text += f"{comment}\n"
        if time:
            text += f"⏰ {time}\n"
        if place:
            text += f"📍 {place}\n"
        if contact:
            text += f"📞 {contact}"
        
        # 280文字以内に調整（Xの投稿制限）
        if len(text) > 280:
            text = text[:277] + "..."
        
        # 投稿
        post_to_x(text, x_client)

# ==== スクリプト実行 ====
if __name__ == "__main__":
    main()
