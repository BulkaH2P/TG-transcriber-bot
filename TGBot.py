import telebot, whisper, os, traceback
from moviepy.editor import AudioFileClip
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()
URL = os.getenv("WEBHOOKURL")
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
model = whisper.load_model("base")


@app.route('/', methods=['GET'])
def index():
    return "Бот работает!"


# 🔗 Основной Webhook обработчик
@app.route(f"/{os.getenv('BOT_TOKEN')}", methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'ok', 200


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


    @bot.message_handler(commands=["start"])
    def greetings(message):
        name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()
        bot.reply_to(message,
                     f"Привет,{name}!\nЯ бот для распознавания аудио.\nОтправь мне голосовое или видео, и я его распознаю 🎙\n❌ Текстовые сообщения не принимаются")


    @bot.message_handler(content_types=["text"])
    def text_block(message):
        try:
            bot.delete_message(message.chat.id, message.message_id)
            bot.send_message(message,
                             f"❌ Я не принимаю текст. Пожалуйста, отправьте голосовое сообщение, кружочек или видео")
        except Exception as e:
            print(f"Не удалось удалить текстовое сообщение: {e}")


    @bot.message_handler(content_types=["voice", "audio", "video", "video_note"])
    def unified_message_handler(message):
        processing_msg = bot.reply_to(message, "⏳ Обрабатываю... Пожалуйста, подождите.")
        if message.voice:
            handle_audio(message, message.voice.file_id, "voice.ogg", processing_msg)
        elif message.audio:
            ext = message.audio.mime_type.split("/")[-1]
            handle_audio(message, message.audio.file_id, f"audio.{ext}", processing_msg)
        elif message.video:
            handle_audio(message, message.video.file_id, "video.mp4", processing_msg)
        elif message.video_note:
            handle_audio(message, message.video_note.file_id, "circle.mp4", processing_msg)


    def handle_audio(message, file_id, filename, processing_msg):
        file = bot.get_file(file_id)
        downloaded_file = bot.download_file(file.file_path)
        with open(filename, "wb") as new:
            new.write(downloaded_file)
        text = recognize(filename)
        bot.delete_message(message.chat.id, processing_msg.message_id)
        reply_text = f"✅ Готово! Вот ваша транскрипция:\n\n{text}" if text.strip() else "❌ Ничего не удалось распознать."
        bot.reply_to(message, reply_text)


    def recognize(filename):
        try:
            audio = AudioFileClip(filename)
            audio.write_audiofile("audio.wav", fps=16000)
            result = model.transcribe("audio.wav", fp16=False, language=None)
            return result["text"]
        except Exception as e:
            traceback.print_exc()
            return f"⚠️Ошибка: {e}"
        finally:
            for f in [filename, "audio.wav"]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception as cleanup_err:
                        print(f"Не удалось удалить файл {f}: {cleanup_err}")
