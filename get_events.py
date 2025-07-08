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

# ==== まいぷれ北近畿のイベント情報を取得 ====
def get_mypl_events():
    """まいぷれ北近畿から福知山関連イベントを取得"""
    events = []
    try:
        # まいぷれ北近畿のイベントカレンダー
        url = "https://maizuru.mypl.net/event/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # イベント情報を取得
        event_items = soup.select(".event-item, .calendar-event, .event-list li, .event-card, article")
        
        for item in event_items:
            try:
                # タイトル取得
                title_elem = item.select_one("h3, h2, .title, .event-title, .article-title")
                title = title_elem.text.strip() if title_elem else ""
                
                # 場所・地域情報を取得
                location_elem = item.select_one(".location, .place, .area, .venue")
                location = location_elem.text.strip() if location_elem else ""
                
                # 福知山関連のイベントかチェック
                if ("福知山" in title or "福知山" in location or 
                    "ドッコイセ" in title or "由良川" in title):
                    
                    # 日付取得
                    date_elem = item.select_one(".date, .event-date, .post-date, .calendar-date")
                    event_date = date_elem.text.strip() if date_elem else ""
                    
                    # 詳細情報取得
                    desc_elem = item.select_one(".description, .summary, .excerpt")
                    description = desc_elem.text.strip() if desc_elem else ""
                    
                    # 時間情報取得
                    time_elem = item.select_one(".time, .event-time, .schedule")
                    time_info = time_elem.text.strip() if time_elem else ""
                    
                    events.append({
                        "title": title,
                        "date": event_date,
                        "location": location,
                        "description": description,
                        "time": time_info,
                        "source": "まいぷれ北近畿",
                        "type": "special_event"
                    })
                    
            except Exception as e:
                print(f"まいぷれイベント解析エラー: {e}")
                continue
                
    except Exception as e:
        print(f"まいぷれサイトアクセスエラー: {e}")
    
    # 今日の日付もチェック
    today = datetime.date.today()
    
    # 今日の特定のイベントページも確認
    try:
        today_url = f"https://maizuru.mypl.net/event/?date={today.strftime('%Y-%m-%d')}"
        response = requests.get(today_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 今日のイベントを詳細に取得
        today_events = soup.select(".today-event, .event-today, .daily-event")
        
        for event in today_events:
            try:
                title_elem = event.select_one("h3, h2, .title")
                title = title_elem.text.strip() if title_elem else ""
                
                location_elem = event.select_one(".location, .place")
                location = location_elem.text.strip() if location_elem else ""
                
                # 福知山関連のイベントかチェック
                if ("福知山" in title or "福知山" in location or 
                    "ドッコイセ" in title or "由良川" in title):
                    
                    events.append({
                        "title": title,
                        "date": f"{today.month}月{today.day}日",
                        "location": location,
                        "description": "",
                        "time": "",
                        "source": "まいぷれ北近畿（今日）",
                        "type": "special_event"
                    })
                    
            except Exception as e:
                print(f"まいぷれ今日のイベント解析エラー: {e}")
                continue
                
    except Exception as e:
        print(f"まいぷれ今日のページアクセスエラー: {e}")
    
    return events

# ==== 定期的な福知山イベントを手動で管理 ====
def get_annual_events():
    """年間の定期イベント情報を手動で管理"""
    today = datetime.date.today()
    events = []
    
    # 年間イベントスケジュール（手動管理）
    annual_events = {
        (8, 15): {"title": "福知山花火大会", "type": "fireworks"},
        (8, 16): {"title": "ドッコイセまつり", "type": "festival"},
        (10, 1): {"title": "福知山市民まつり", "type": "festival"},
        (11, 23): {"title": "福知山マラソン", "type": "sports"},
        (12, 31): {"title": "福知山カウントダウン", "type": "countdown"},
        (1, 1): {"title": "福知山初詣", "type": "newyear"},
        (4, 1): {"title": "福知山さくらまつり", "type": "festival"},
        (7, 15): {"title": "鬼力の由良川夏まつり", "type": "festival"},
    }
    
    # 今日が該当するイベントをチェック
    today_key = (today.month, today.day)
    if today_key in annual_events:
        event_info = annual_events[today_key]
        events.append({
            "title": event_info["title"],
            "date": f"{today.month}月{today.day}日",
            "source": "年間スケジュール",
            "type": "special_event"
        })
    
    return events

# ==== 福知山市公式サイトのイベント情報を取得 ====
def get_city_special_events():
    """福知山市公式サイトから特別なイベント情報を取得"""
    events = []
    try:
        # 福知山市のイベント・お知らせページ（実際に存在するURL）
        urls = [
            "https://www.city.fukuchiyama.lg.jp/soshiki/list5-1.html",  # イベント一覧
            "https://www.city.fukuchiyama.lg.jp/site/promotion/",  # いがいと！福知山（プロモーション）
        ]
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        for url in urls:
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, "html.parser")
                
                # 新着情報やイベント情報を取得
                news_items = soup.select(".news-item, .event-item, .article-item, .info-item")
                
                for item in news_items:
                    try:
                        # タイトル取得
                        title_elem = item.select_one("a, h3, h2, .title")
                        title = title_elem.text.strip() if title_elem else ""
                        
                        # 日付取得
                        date_elem = item.select_one(".date, .post-date, .event-date")
                        event_date = date_elem.text.strip() if date_elem else ""
                        
                        # 特別なイベントかチェック
                        special_keywords = ["花火", "祭り", "まつり", "フェス", "コンサート", "イベント", "大会"]
                        if any(keyword in title for keyword in special_keywords):
                            events.append({
                                "title": title,
                                "date": event_date,
                                "source": "市公式",
                                "type": "special_event"
                            })
                            
                    except Exception as e:
                        print(f"市公式イベント解析エラー: {e}")
                        continue
                        
            except Exception as e:
                print(f"市公式サイトアクセスエラー ({url}): {e}")
                continue
                
    except Exception as e:
        print(f"市公式サイト全体エラー: {e}")
    
    return events

# ==== 今日の日付に関連するイベントをフィルタリング ====
def filter_today_events(events):
    """今日の日付に関連するイベントをフィルタリング"""
    today = datetime.date.today()
    today_events = []
    
    for event in events:
        event_date = event.get("date", "")
        title = event.get("title", "")
        
        # 今日の日付が含まれているかチェック
        date_patterns = [
            f"{today.month}月{today.day}日",
            f"{today.month}/{today.day}",
            f"{today.year}年{today.month}月{today.day}日",
            f"{today.year}/{today.month}/{today.day}",
        ]
        
        # 日付文字列に今日の日付が含まれているかチェック
        is_today = any(pattern in event_date for pattern in date_patterns)
        
        # タイトルに「今日」「本日」が含まれているかチェック
        is_today_title = any(keyword in title for keyword in ["今日", "本日"])
        
        if is_today or is_today_title:
            today_events.append(event)
    
    return today_events

# ==== 特別イベントを投稿用テキストに整形 ====
def format_special_event_text(event):
    """特別イベントをX投稿用のテキストに整形"""
    title = event.get("title", "")
    date = event.get("date", "")
    source = event.get("source", "")
    
    # イベントタイプに応じた絵文字
    emoji = "🎆"
    if "花火" in title:
        emoji = "🎆"
    elif "祭り" in title or "まつり" in title:
        emoji = "🎭"
    elif "フェス" in title:
        emoji = "🎪"
    elif "コンサート" in title:
        emoji = "🎵"
    elif "大会" in title:
        emoji = "🏆"
    else:
        emoji = "🎉"
    
    text = f"{emoji} 福知山市イベント情報\n"
    text += f"📅 {title}\n"
    
    if date:
        text += f"日時: {date}\n"
    
    text += f"情報源: {source}\n"
    text += "#福知山市 #イベント情報"
    
    # 280文字以内に調整
    if len(text) > 280:
        text = text[:277] + "..."
    
    return text

# ==== イベントをXに投稿する関数 ====
def post_to_x(text, client):
    try:
        client.update_status(status=text)
        print("✅ 投稿完了: ", text[:30], "...")
    except Exception as e:
        print("⚠️ 投稿エラー:", e)

# ==== 市役所カレンダーのイベント取得（既存の機能） ====
def get_city_calendar_events():
    """福知山市役所のカレンダーから今日のイベントを取得"""
    events = []
    try:
        today = datetime.date.today()
        url = f"https://www.city.fukuchiyama.lg.jp/calendar/index.php?dsp=1&y={today.year}&m={today.month}&d={today.day}"
        
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.content, "html.parser")
        
        today_day_elem = soup.select_one(f'.t_day span:-soup-contains("{today.day}")')
        if not today_day_elem:
            return events
        
        today_calendar_day = today_day_elem.find_parent("dl", class_="calendar_day")
        if not today_calendar_day:
            return events
        
        event_boxes = today_calendar_day.select(".cal_event_box")
        
        for event_box in event_boxes:
            try:
                title_elem = event_box.select_one(".article_title a")
                title = title_elem.text.strip() if title_elem else "タイトル不明"
                
                category_elem = event_box.select_one(".cal_event_icon span")
                category = category_elem.text.strip() if category_elem else ""
                
                comment_elem = event_box.select_one(".cal_event_comment")
                comment = comment_elem.text.strip() if comment_elem else ""
                
                time_dt = event_box.select_one('dt:has(img[alt="開催時間"])')
                time = time_dt.find_next_sibling('dd').text.strip() if time_dt and time_dt.find_next_sibling('dd') else ""
                
                place_dt = event_box.select_one('dt:has(img[alt="開催場所"])')
                place = place_dt.find_next_sibling('dd').text.strip() if place_dt and place_dt.find_next_sibling('dd') else ""
                
                contact_dt = event_box.select_one('dt:has(img[alt="お問い合わせ"])')
                contact = contact_dt.find_next_sibling('dd').text.strip() if contact_dt and contact_dt.find_next_sibling('dd') else ""
                
                events.append({
                    "title": title,
                    "category": category,
                    "comment": comment,
                    "time": time,
                    "place": place,
                    "contact": contact,
                    "source": "市役所カレンダー",
                    "type": "calendar_event"
                })
                
            except Exception as e:
                print(f"カレンダーイベント解析エラー: {e}")
                continue
                
    except Exception as e:
        print(f"市役所カレンダーアクセスエラー: {e}")
    
    return events

# ==== カレンダーイベントを投稿用テキストに整形 ====
def format_calendar_event_text(event, index, total):
    """カレンダーイベントをX投稿用のテキストに整形"""
    title = event.get("title", "")
    category = event.get("category", "")
    comment = event.get("comment", "")
    time = event.get("time", "")
    place = event.get("place", "")
    contact = event.get("contact", "")
    
    text = f"📅 {title}"
    if total > 1:
        text += f" ({index}/{total})"
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
    
    # 280文字以内に調整
    if len(text) > 280:
        text = text[:277] + "..."
    
    return text

# ==== メイン処理 ====
def main():
    # Twitterクライアントを作成
    x_client = create_twitter_client()
    
    # 今日の天気情報を投稿
    weather = get_weather_info()
    weather_text = format_weather_text(weather)
    post_to_x(weather_text, x_client)
    
    print("=== 特別イベント情報を取得中 ===")
    
    # 観光協会のイベント情報を取得
    tourism_events = get_tourism_events()
    print(f"観光協会イベント: {len(tourism_events)}件")
    
    # まいぷれ北近畿のイベント情報を取得
    mypl_events = get_mypl_events()
    print(f"まいぷれ北近畿イベント: {len(mypl_events)}件")
    
    # 年間定期イベントをチェック
    annual_events = get_annual_events()
    print(f"年間定期イベント: {len(annual_events)}件")
    
    # 市公式サイトのイベント情報を取得
    city_special_events = get_city_special_events()
    print(f"市公式特別イベント: {len(city_special_events)}件")
    
    # 特別イベントをまとめる
    all_special_events = tourism_events + mypl_events + annual_events + city_special_events
    
    # 今日の特別イベントをフィルタリング
    today_special_events = filter_today_events(all_special_events)
    print(f"今日の特別イベント: {len(today_special_events)}件")
    
    # 特別イベントを投稿
    for event in today_special_events:
        if event.get("source") == "まいぷれ北近畿" or event.get("source") == "まいぷれ北近畿（今日）":
            special_text = format_mypl_event_text(event)
        else:
            special_text = format_special_event_text(event)
        post_to_x(special_text, x_client)
    
    print("=== 市役所カレンダーイベントを取得中 ===")
    
    # 市役所カレンダーのイベント情報を取得
    calendar_events = get_city_calendar_events()
    print(f"今日のカレンダーイベント: {len(calendar_events)}件")
    
    if len(calendar_events) == 0 and len(today_special_events) == 0:
        # イベントがない場合
        today = datetime.date.today()
        no_events_text = f"📅 {today.month}月{today.day}日の福知山市\n今日は特別なイベントはありません。\n素敵な一日をお過ごしください！"
        post_to_x(no_events_text, x_client)
    else:
        # カレンダーイベントを投稿
        for i, event in enumerate(calendar_events, 1):
            calendar_text = format_calendar_event_text(event, i, len(calendar_events))
            post_to_x(calendar_text, x_client)
    
    print("=== 処理完了 ===")

# ==== スクリプト実行 ====
if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
