import os, sys
import telepot


def getBot():
    token = os.getenv("TELE_TOKEN")
    bot = telepot.Bot(token)
    return bot

def send_bot_message(bot, msg):
    bot.sendMessage(chat_id=6615017798, text=msg)

if __name__ == "__main__":
    # 테스트 코드
    bot = getBot()
    send_bot_message(bot, "test send")