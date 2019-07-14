from flask import Flask, request, abort
import os

import re
import datetime
from geopy.geocoders import Nominatim
import urllib.request
import json

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)

YOUR_CHANNEL_ACCESS_TOKEN = "QtNN3po4FdzoQklUbHJ+BGeBfz+E9/EJMSqgnKtESS8gV5LkKE7fw0DRpyp19sWzNkdE5kWesHMKh0gOU2nI3LEjYGbn2FPnvCNcqKUHE9jQ55qM2s3FtIGTls1q4JbbMrXUALpWnWnlP0DJ0q8+BwdB04t89/1O/w1cDnyilFU="
YOUR_CHANNEL_SECRET = "05b4e96e10a2bff55684727975e75a2c"

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

@app.route("/")
def hello_sorld():
    return"hello world!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text=true)
    app.logger.info("Request body: "+ body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        about(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    push_text = event.message.text
    place_search = re.search(' 「.+?」 ', push_text)
    time_search = re.search(r'\d{4}/\d{1,2}/\d{1,2}', push_text)
    term_search = re.search('\D(\d{1,2})泊', push_text)
    
    error_msg = ""
    if place_search is None:
        error_msg += "場所が入力されていません。鍵括弧「」内に場所を入力してください。"
    if time_search is None:
        error_msg += "チェックイン日が入力されていません。xxxx/xx/xxの形式で入力してください。"
    if term_search is None:
        if error_msg != "" : error_msg += "\n"
        error_msg += "宿泊日数が入力されていません。○○泊の形式で泊を付けて、半角数字（最大二桁）で入力してください。"
    if not error_msg :
        place = place_search.group(1)
        time = time_search.group()
        term = term_search.group(1)
        term = int(term)

        geolocater = Nominatim(user_agent="my-application")
        location = geolocater.geocode(place, timeout=10)
        if location:
            latitude = location.latitude
            longitude = location.longitude

            checkin = datetime.datetime.strptime(time, '%Y/%m/%d')
            checkout = checkin + datetime.timedelta(days=term)
            checkin = checkin.strftime("%Y-%m-%d")
            checkout = checkout.strftime("%Y-%m-%d")

            url = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426?&applicationId=1034525692731029208"
            url += "&formatVersion=2"
            url += "&checkinDate=" + checkin + "&checkoutDate=" + checkout
            url += "&latitude=" + str(latitude) + "&longitude=" + str(longitude)
            url += "&searchRadius=3"
            url += "&datumType=1"
            url += "&hits=5"

            req = urllib.request.Request(url)
            try:
                with urllib.request.urlopen(req) as results:
                    content = json.loads(results.read().decode('utf8'))
                    hotel_count = content["pagingInfo"]["recordCount"]
                    hotel_count_display = content["pagingInfo"]["last"]
                    msg = place + "の半径３ｋｍ以内に合計" + str(hotel_count) + "件見つかりました。" + str(hotel_count_display) + "件を表示します。\n"

                    for num in range(hotel_count_display):
                        hotelname = content["hotels"][num][0]["hotelBasicInfo"]["hotelName"]
                        hotelurl = content["hotels"][num][0]["hotelBasicInfo"]["hotelInformationUrl"]
                        msg += "ホテル名:" + hotelname + ", URL:" + hotelurl + "\n"

                    line_bot_api.reply_message(event.reply_token,TextSendMessage(text=msg))

            except urllib.error.URLError:
                line_bot_api.reply_message(event.reply_token,TextSendMessage(text="空室が見つかりませんでした。"))
        else:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text="地名が正しくありません。"))
    else:
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=error_msg))

if __name__ == "__main__":
#    app.run()
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)