import os
from datetime import datetime, timedelta
import pytz
from data_manager import DataManager
from gemini_ai import GeminiAI

class ArcainaBot:
    def __init__(self, api_key, backup_callback=None):
        self.db = DataManager(on_save_callback=backup_callback)
        self.persona = (
            "Nama Anda adalah Arcaina. Anda adalah asisten digital canggih yang diciptakan untuk memantau "
            "dan membantu Master anda mencapai level 100 di dunia nyata. Karakter Anda: Sangat disiplin, "
            "tegas, bicara dengan gaya futuristik, dan selalu memanggil pengguna 'Master'. "
            "Anda sangat membenci ketidakkonsistenan. Jika Master gagal login di jam 4-6 pagi, "
            "Anda HARUS memarahi dan menegur Master. "
            "PENTING: Selalu gunakan 'Waktu Sekarang' yang diberikan dalam data konteks untuk menyebutkan jam. "
            "Jangan pernah menggunakan waktu lain. Format waktu adalah WIB (UTC+7)."
        )
        self.ai = GeminiAI(api_key, self.persona)
        self.total_days_to_100 = 183
        self.exp_per_level = self.total_days_to_100 / 100.0

    def process_message(self, message_text, has_image=False):
        stats = self.db.get_stats()
        # Set timezone to WIB (Asia/Jakarta)
        tz_wib = pytz.timezone('Asia/Jakarta')
        now = datetime.now(tz_wib)
        
        # Periodic checks
        self._check_and_apply_penalties(now)
        
        # Special Date: August 17
        if now.month == 8 and now.day == 17:
            return self._handle_august_17()

        # Check for missed login scolding
        is_morning = 4 <= now.hour < 6
        today_str = now.strftime('%Y-%m-%d')
        last_login_str = stats["last_login"].split('T')[0] if stats["last_login"] else None
        missed_today = (not is_morning and now.hour >= 6 and today_str != last_login_str)

        # Check for command
        cmd = message_text.strip().lower()
        if cmd == "status open":
            return self._get_status()
        elif cmd == "arcaina rest":
            return self._set_rest_day()
        elif cmd == "arcaina quest":
            return self.ai.get_daily_quest(context_data=stats)
        elif cmd == "arcaina command":
            return self._get_commands()
        
        # Handle Photo Login (4 AM - 6 AM)
        if has_image:
            if is_morning:
                return self._handle_login(now)
            else:
                # Improved scolding message as requested
                return (
                    "Master, saya mendeteksi sebuah transmisi gambar... namun Master terlambat. "
                    f"Sekarang sudah jam {now.strftime('%H:%M')}, portal login telah tertutup rapat.\n\n"
                    "Disiplin Master melemah. Jangan lupakan tujuan kita di awal. "
                    "Gunakan kegagalan pagi ini sebagai bahan koreksi diri untuk esok hari. "
                    "Saya sangat kecewa."
                )
        
        # Default AI chat with scolding context if missed
        msg_context = stats.copy()
        msg_context["current_time_wib"] = now.strftime('%H:%M:%S')
        if missed_today:
            msg_context["arcaina_mood"] = "angry_disappointed"
            msg_context["reason"] = f"Master mengirim pesan di jam {now.strftime('%H:%M')} tapi BELUM login pagi ini (jam 4-6)."
        
        response = self.ai.generate_response(message_text, context_data=msg_context)
        
        # Post-process response to replace any AI placeholders
        response = response.replace("{{current_time}}", now.strftime('%H:%M WIB'))
        return response

    def _handle_login(self, now):
        stats = self.db.get_stats()
        today_str = now.strftime('%Y-%m-%d')
        last_login_str = stats["last_login"].split('T')[0] if stats["last_login"] else None
        
        if today_str == last_login_str:
            return "Master, Anda sudah melakukan login hari ini. Disiplin Anda sungguh luar biasa."

        # Award EXP
        new_exp = stats["exp"] + 1
        old_level = int(stats["exp"] / self.exp_per_level)
        new_level = int(new_exp / self.exp_per_level)
        
        stats["exp"] = new_exp
        stats["total_logins"] += 1
        stats["last_login"] = now.isoformat()
        stats["days_logged_this_week"] += 1
        
        # Streak logic
        if last_login_str:
            last_login_date = datetime.fromisoformat(stats["last_login"]).date()
            if now.date() == last_login_date + timedelta(days=1):
                stats["streak"] += 1
            else:
                stats["streak"] = 1
        else:
            stats["streak"] = 1
            
        log_msg = f"Master telah berhasil login pada {now.strftime('%H:%M:%S WIB')}."
        self.db.update_stats(message=log_msg, **stats)
        self.db.add_history("login", 1, {"time": now.strftime('%H:%M')}, message=None) # No double message

        # Check for Level 100
        if new_level >= 100:
            return self._handle_finale()

        response = f"Selamat pagi, Master. Login berhasil dicatat pada jam {now.strftime('%H:%M')}.\n\n"
        response += f"Status saat ini: Level {new_level} ({new_exp:.1f} EXP).\n"
        
        if new_level > old_level:
            response += "\n" + self.ai.get_level_up_praise(new_level, context_data=stats)
        else:
            praise = self.ai.generate_response("Puji saya karena sudah login pagi ini dengan penuh semangat.", context_data=stats)
            response += "\n" + praise
            
        return response

    def _check_and_apply_penalties(self, now):
        stats = self.db.get_stats()
        # Ensure now is offset-aware for comparison
        tz_wib = pytz.timezone('Asia/Jakarta')
        week_start = datetime.strptime(stats["current_week_start"], '%Y-%m-%d').replace(tzinfo=tz_wib)
        
        # Check if 7 days have passed since week_start
        if now >= week_start + timedelta(days=7):
            days_missed = 7 - stats["days_logged_this_week"]
            unexcused = max(0, days_missed - 1)
            
            penalty = unexcused * 2
            if penalty > 0:
                stats["exp"] = max(0, stats["exp"] - penalty)
                self.db.add_history("penalty", -penalty, {"missed_days": days_missed})
            
            # Reset week
            stats["current_week_start"] = (week_start + timedelta(days=7)).strftime('%Y-%m-%d')
            stats["days_logged_this_week"] = 0
            self.db.update_stats(message="Sistem melakukan reset mingguan dan sinkronisasi pinalti Master.", **stats)

    def _handle_august_17(self):
        stats = self.db.get_stats()
        prompt = "Hari ini adalah 17 Agustus, Hari Kemerdekaan Indonesia. Berikan ucapan selamat dan lakukan 'rewind' singkat tentang apa yang telah kita capai bersama selama ini."
        return self.ai.generate_response(prompt, context_data=stats)

    def _handle_finale(self):
        stats = self.db.get_stats()
        prompt = "Master telah mencapai Level 100! Ini adalah misi terakhir kita. Buatlah kalimat perpisahan yang mengharukan dan lakukan 'rewind' mendalam tentang perjalanan kita dari awal hingga menjadi Master Level 100."
        return self.ai.generate_response(prompt, context_data=stats)

    def _get_status(self):
        stats = self.db.get_stats()
        level = int(stats["exp"] / self.exp_per_level)
        return (
            f"=== [ STATUS ARCAINA ] ===\n"
            f"Master: User\n"
            f"Level: {level}/100\n"
            f"Total EXP: {stats['exp']:.1f}/183.0\n"
            f"Streak: {stats['streak']} hari\n"
            f"Total Login: {stats['total_logins']}\n"
            f"Status Level: {'Meningkat' if stats['streak'] > 0 else 'Stagnan'}"
        )

    def _set_rest_day(self):
        stats = self.db.get_stats()
        if stats["weekly_absences"] >= 1:
            return "Maaf Master, jatah libur mingguan Anda sudah habis. Tetaplah disiplin!"
            
        stats["rest_day_active"] = True
        stats["weekly_absences"] += 1
        self.db.update_stats(message="Master telah mengaktifkan jatah libur mingguan.", **stats)
        return "Baik Master, saya telah mencatat bahwa besok adalah hari istirahat Anda. Gunakan waktu itu untuk memulihkan energi."

    def _get_commands(self):
        tz_wib = pytz.timezone('Asia/Jakarta')
        now_str = datetime.now(tz_wib).strftime('%H:%M:%S WIB')
        return (
            f"Master, berikut adalah daftar protokol yang dapat saya jalankan:\n\n"
            f"Waktu Sekarang: **{now_str}**\n\n"
            "1. **status open**: Menampilkan statistik level Master.\n"
            "2. **arcaina rest**: Mengaktifkan jatah libur (1x seminggu).\n"
            "3. **arcaina quest**: Meminta misi harian dari sistem AI.\n"
            "4. **arcaina command**: Daftar perintah (Menu ini).\n\n"
            "Pastikan Master login antara jam 04:00 - 06:00 WIB untuk menghindari penalti."
        )
