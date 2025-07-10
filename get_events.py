import datetime
import os
import requests
from bs4 import BeautifulSoup
import tweepy

# ==== X(Twitter) API認証 ====
def create_twitter_client_v2():
    bearer_token = os.environ["X_BEARER_TOKEN"]
    api_key = os.environ["X_API_KEY"]
    api_secret = os.environ["X_API_SECRET"]
    access_token = os.environ["X_ACCESS_TOKEN"]
    access_secret = os.environ["X_ACCESS_SECRET"]
    
    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )
    return client

# ==== 天気情報を取得 ====
def get_weather_info():
    try:
        url = "https://www.jma.go.jp/bosai/forecast/data/forecast/260000.json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        today_weather = data[0]['timeSeries'][0]['areas'][0]
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

def format_weather_text(weather):
    if not weather:
        return "🌤️ 福知山市の天気情報を取得できませんでした"
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

# ==== 修正版：まいぷれ北近畿イベント取得 ====
def get_mypl_events():
    events = []
    try:
        url = "https://maizuru.mypl.net/event/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # より汎用的なセレクタを使用
        event_items = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['event', 'calendar', 'item', 'card', 'list']
        ))
        
        # テキストベースでの検索も追加
        if not event_items:
            # すべてのdivやarticleから福知山関連を検索
            all_elements = soup.find_all(['div', 'article', 'section', 'li'])
            for elem in all_elements:
                text = elem.get_text(strip=True)
                if any(keyword in text for keyword in ["福知山", "ドッコイセ", "由良川"]):
                    event_items.append(elem)
        
        print(f"まいぷれ: {len(event_items)}件の要素を発見")
        
        for item in event_items:
            try:
                # より柔軟なタイトル取得
                title = ""
                for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    title_elem = item.find(tag)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                
                if not title:
                    # aタグのテキストをタイトルとして使用
                    link_elem = item.find('a')
                    if link_elem:
                        title = link_elem.get_text(strip=True)
                
                # 福知山関連のイベントのみ抽出
                if title and any(keyword in title for keyword in ["福知山", "ドッコイセ", "由良川"]):
                    # 日付情報を取得
                    date_text = ""
                    date_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'date' in x.lower())
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                    
                    # 場所情報を取得
                    location_text = ""
                    location_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and any(
                        keyword in x.lower() for keyword in ['location', 'place', 'area', 'venue']
                    ))
                    if location_elem:
                        location_text = location_elem.get_text(strip=True)
                    
                    events.append({
                        "title": title,
                        "date": date_text,
                        "location": location_text,
                        "source": "まいぷれ北近畿",
                        "type": "special_event"
                    })
                    print(f"まいぷれイベント取得: {title}")
                    
            except Exception as e:
                print(f"まいぷれイベント解析エラー: {e}")
                continue
                
    except Exception as e:
        print(f"まいぷれサイトアクセスエラー: {e}")
    
    return events

# ==== 年間定期イベント ====
def get_annual_events():
    today = datetime.date.today()
    events = []
    annual_events = {
        (7, 26): {"title": "あやべ水無月まつり花火大会2025 綾部市第1市民グラウンド 京都府綾部市川糸町天王森", "type": "fireworks"},
        (8, 2): {"title": "鬼力の由良川夏まつり", "type": "festival"},
        (8, 11): {"title": "福知山HANABI2025", "type": "fireworks"},
        (8, 12): {"title": "ドッコイセまつり(午前11：00～ドッコイセこども大会)", "type": "festival"},
        (8, 14): {"title": "ドッコイセまつり(午後7：30～オープニングイベント)", "type": "festival"},
        (8, 15): {"title": "ドッコイセまつり(午後8：00～9：00一般参加)", "type": "festival"},
        (8, 23): {"title": "ドッコイセまつり(午後7：15～8：00学生大会（広小路）", "type": "festival"},
        (8, 24): {"title": "ドッコイセまつり(午後7：00～9：00『駅北で市民総踊り』", "type": "festival"},
        (11, 23): {"title": "福知山マラソン", "type": "sports"},
        (4, 1): {"title": "福知山さくらまつり", "type": "festival"},
    }
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

# ==== 修正版：市公式サイトイベント ====
def get_city_special_events():
    events = []
    try:
        urls = [
            "https://www.city.fukuchiyama.lg.jp/calendar/",  # 修正されたURL
            "https://www.city.fukuchiyama.lg.jp/soshiki/list5-1.html",
            "https://dokkoise.com/category/event/",  # 福知山観光協会のイベント情報
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        for url in urls:
            try:
                print(f"市公式サイト取得中: {url}")
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                
                # より汎用的なセレクタ
                news_items = soup.find_all(['div', 'article', 'li'], class_=lambda x: x and any(
                    keyword in x.lower() for keyword in ['news', 'event', 'item', 'info', 'calendar']
                ))
                
                # テキストベースでの検索も追加
                if not news_items:
                    all_elements = soup.find_all(['div', 'article', 'section', 'li'])
                    for elem in all_elements:
                        text = elem.get_text(strip=True)
                        if any(keyword in text for keyword in ["花火", "祭り", "まつり", "フェス", "コンサート", "イベント", "大会"]):
                            news_items.append(elem)
                
                print(f"市公式 ({url}): {len(news_items)}件の要素を発見")
                
                for item in news_items:
                    try:
                        # タイトル取得
                        title = ""
                        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                            title_elem = item.find(tag)
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                break
                        
                        if not title:
                            link_elem = item.find('a')
                            if link_elem:
                                title = link_elem.get_text(strip=True)
                        
                        # 日付取得
                        date_text = ""
                        date_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'date' in x.lower())
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                        
                        # イベント関連キーワードでフィルタリング
                        if title and any(keyword in title for keyword in ["花火", "祭り", "まつり", "フェス", "コンサート", "イベント", "大会"]):
                            events.append({
                                "title": title,
                                "date": date_text,
                                "source": "市公式" if "city.fukuchiyama" in url else "観光協会",
                                "type": "special_event"
                            })
                            print(f"市公式イベント取得: {title}")
                            
                    except Exception as e:
                        print(f"市公式イベント解析エラー: {e}")
                        continue
                        
            except Exception as e:
                print(f"市公式サイトアクセスエラー ({url}): {e}")
                continue
                
    except Exception as e:
        print(f"市公式サイト全体エラー: {e}")
    
    return events

# ==== イベントフィルタ ====
def filter_today_events(events):
    today = datetime.date.today()
    today_events = []
    date_patterns = [
        f"{today.month}月{today.day}日",
        f"{today.month}/{today.day}",
        f"{today.year}年{today.month}月{today.day}日",
        f"{today.year}/{today.month}/{today.day}",
    ]
    for event in events:
        event_date = event.get("date", "")
        title = event.get("title", "")
        is_today = any(pattern in event_date for pattern in date_patterns)
        is_today_title = any(keyword in title for keyword in ["今日", "本日"])
        if is_today or is_today_title:
            today_events.append(event)
    return today_events

# ==== 投稿整形 ====
def format_special_event_text(event):
    title = event.get("title", "")
    date = event.get("date", "")
    source = event.get("source", "")
    emoji = "🎉"
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
    text = f"{emoji} 福知山市イベント情報\n📅 {title}\n"
    if date:
        text += f"日時: {date}\n"
    text += f"情報源: {source}\n#福知山市 #イベント情報"
    if len(text) > 280:
        text = text[:277] + "..."
    return text

# ==== 投稿関数 ====
def post_to_x(text, client):
    try:
        client.create_tweet(text=text)  # ← ここが重要
        print("✅ 投稿完了: ", text[:30], "...")
    except Exception as e:
        print("⚠️ 投稿エラー:", e)

# ==== メイン処理 ====
def main():
    x_client = create_twitter_client_v2()  # ← 修正ポイント

    weather = get_weather_info()
    weather_text = format_weather_text(weather)
    post_to_x(weather_text, x_client)

    print("=== 特別イベント情報を取得中 ===")
    tourism_events = []  # ← 今は空リストでOK
    mypl_events = get_mypl_events()
    annual_events = get_annual_events()
    city_special_events = get_city_special_events()

    all_special_events = tourism_events + mypl_events + annual_events + city_special_events
    today_special_events = filter_today_events(all_special_events)

    for event in today_special_events:
        special_text = format_special_event_text(event)
        post_to_x(special_text, x_client)

    print("=== 処理完了 ===")

if __name__ == "__main__":
    main()

