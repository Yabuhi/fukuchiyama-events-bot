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

# ==== イベントをXに投稿する関数 ====
def post_to_x(text, client):
    try:
        client.update_status(status=text)
        print("✅ 投稿完了: ", text[:30], "...")
    except Exception as e:
        print("⚠️ 投稿エラー:", e)

# ==== イベント収集 ====
today = datetime.date.today()
url = f"https://www.city.fukuchiyama.lg.jp/calendar/index.php?dsp=1&y={today.year}&m={today.month}&d={today.day}"

headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.content, "html.parser")

today_day_elem = soup.select_one(f'.t_day span:-soup-contains("{today.day}")')
if not today_day_elem:
    print("今日の日付が見つかりませんでした")
    exit()

today_calendar_day = today_day_elem.find_parent("dl", class_="calendar_day")
if not today_calendar_day:
    print("今日のカレンダー要素が見つかりませんでした")
    exit()

events = today_calendar_day.select(".cal_event_box")
print(f"今日({today.month}月{today.day}日)のイベント数: {len(events)}")

if len(events) == 0:
    print("今日はイベントがありません")
    exit()

# Twitterクライアントを作成
x_client = create_twitter_client()

# イベントごとに投稿
for event in events:
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
    text = f"📅 {title}\n"
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
