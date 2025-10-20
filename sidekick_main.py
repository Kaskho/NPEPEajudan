import os
import logging
import time
from flask import Flask, request, abort
import telebot
from sidekick_logic import SidekickLogic
from config_sidekick import Config  # Impor dari file config baru
from waitress import serve

# ==========================
#  🔧 KONFIGURASI & INISIALISASI
# ==========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = None
sidekick_logic = None

# ==========================
#  🚀 INISIALISASI BOT
# ==========================
try:
    if all([Config.SIDEKICK_BOT_TOKEN(), Config.WEBHOOK_BASE_URL(), Config.DATABASE_URL()]):
        bot = telebot.TeleBot(Config.SIDEKICK_BOT_TOKEN(), threaded=False)
        sidekick_logic = SidekickLogic(bot)
    else:
        logger.critical("FATAL: Variabel lingkungan penting untuk Sidekick tidak ditemukan.")
except Exception as e:
    logger.critical(f"Terjadi error saat inisialisasi Sidekick Bot: {e}", exc_info=True)

# ==========================
#  🌐 RUTE WEB FLASK
# ==========================
@app.route(f'/{Config.SIDEKICK_BOT_TOKEN()}', methods=['POST'])
def webhook():
    if sidekick_logic and request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            logger.error(f"Pengecualian di webhook Sidekick: {e}", exc_info=True)
        return "OK", 200
    else:
        abort(403)

@app.route('/health/sidekick', methods=['GET'])
def health_check():
    logger.info("Ping 'Health Check' Sidekick diterima.")
    if sidekick_logic:
        sidekick_logic.check_and_run_schedules()
    return "", 204  # 204 No Content adalah respons yang efisien

@app.route('/sidekick')
def index():
    return "🐸 Sidekick Bot NPEPE hidup - webhook diaktifkan.", 200

# ==========================
#  ⚡ TITIK MASUK UTAMA
# ==========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10001))
    if bot and sidekick_logic:
        webhook_url = f"{Config.WEBHOOK_BASE_URL()}/{Config.SIDEKICK_BOT_TOKEN()}"
        logger.info("Memulai Sidekick Bot dan mengatur webhook...")
        try:
            bot.remove_webhook()
            time.sleep(0.5)
            success = bot.set_webhook(url=webhook_url)
            if success:
                logger.info("✅ Webhook Sidekick berhasil diatur.")
            else:
                logger.error("❌ Gagal mengatur webhook Sidekick.")
        except Exception as e:
            logger.error(f"Error saat mengkonfigurasi webhook Sidekick: {e}", exc_info=True)
        
        serve(app, host="0.0.0.0", port=port)
    else:
        logger.error("Sidekick Bot tidak diinisialisasi. Berjalan dalam mode server terdegradasi.")
        serve(app, host="0.0.0.0", port=port)
