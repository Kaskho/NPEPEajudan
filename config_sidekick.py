# config_sidekick.py
import os

class Config:
    """
    Kelas untuk mengelola semua variabel konfigurasi untuk Sidekick Bot.
    """
    @staticmethod
    def SIDEKICK_BOT_TOKEN(): 
        return os.environ.get("SIDEKICK_BOT_TOKEN")
    
    @staticmethod
    def WEBHOOK_BASE_URL(): 
        return os.environ.get("WEBHOOK_BASE_URL")

    @staticmethod
    def MAIN_BOT_USER_ID(): 
        return os.environ.get("MAIN_BOT_USER_ID")

    @staticmethod
    def GROUP_CHAT_ID(): 
        return os.environ.get("GROUP_CHAT_ID")
        
    # ID numerik dari pemilik grup untuk menerima laporan.
    @staticmethod
    def GROUP_OWNER_ID():
        return os.environ.get("GROUP_OWNER_ID")

    # Menggunakan URL database terpisah untuk menghindari konflik
    @staticmethod
    def DATABASE_URL(): 
        return os.environ.get("SIDEKICK_DATABASE_URL")
        
    # Kunci API untuk layanan Groq AI
    @staticmethod
    def GROQ_API_KEY():
        return os.environ.get("GROQ_API_KEY")
