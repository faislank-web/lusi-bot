import os
import telebot
import requests
import logging
import random
import io
import html
import re
import time
import socket
import pytz
import asyncio
from telebot import types, apihelper
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from PIL import Image, ImageDraw, ImageFont, ImageOps
import google.genai as genai 
from groq import Groq
from huggingface_hub import hf_hub_download, upload_file
from pyrogram import Client
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# ==========================================
# [ 0. DNS PATCH - JALAN NINJA ANTI-RESET ]
# ==========================================
TELEGRAM_IP = '149.154.167.221'
def apply_dns_patch():
    old_getaddrinfo = socket.getaddrinfo
    def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host == 'api.telegram.org':
            return old_getaddrinfo(TELEGRAM_IP, port, family, type, proto, flags)
        return old_getaddrinfo(host, port, family, type, proto, flags)
    socket.getaddrinfo = new_getaddrinfo

apply_dns_patch()

# --- [ KONFIGURASI DATASET ABADI ] ---
REPO_ID = "faislank/data-nobar" 
HF_TOKEN = os.getenv("HF_TOKEN")
INDEX_FILE = "index_lucy.txt"
STRING_SESSION = "1BVtsOHcBu7An7obS9dUx1IFGlfA79XooFPHh5huih7kKqfvyFOSDs1NOUMUFBG1CewaL3Ngv2Aw5dfOOiQlkDua01XIoBZCRhubfGD4gIDi92VwCV-dNE3r1iFKiwm63HxSUo--O2tWgE-VwNVnCKQF3ufbTiBwQnV3Xguwduak_EJOd4V9FPY8KW3fxGbU1AjbsXJeJZXGEYdw4PoY88uPLEQURU5WdejuBKTkmyrLnYUCReVfRXuHQ-6dIzBBR6PjPwmbTpUGNIXVHFyLl3A_sqZdoLo146eX21N4nD4Bcdi3x98YMc6BsXdOopDJjYCa-UjfWALi776MBfg3fyKZl4IcQsEw="

def download_index():
    if os.path.exists(INDEX_FILE): return 
    try:
        hf_hub_download(repo_id=REPO_ID, filename=INDEX_FILE, local_dir=".", repo_type="dataset", token=HF_TOKEN)
        print("✅ Database film berhasil diunduh dari Cloud!")
    except Exception as e:
        print(f"ℹ️ Belum ada database di Cloud, mulai baru.")

def sync_ke_cloud():
    try:
        upload_file(path_or_fileobj=INDEX_FILE, path_in_repo=INDEX_FILE, repo_id=REPO_ID, repo_type="dataset", token=HF_TOKEN)
    except:
        pass

# --- [ 1. DATA AKSES & KONFIGURASI ] ---
TELEGRAM_TOKEN = "8485819414:AAFuMaapg-DJ6s5FpNjRPFUU6gAr9Cv18aw"
GEMINI_KEY = "AIzaSyAfORMxFIT7pIG1PmZwcG6LnmQ0MS6g5l8"
GROQ_KEY = "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"
TMDB_KEY = "61e2290429798c561450eb56b26de19b"
API_ID = 36241979 
API_HASH = "a095fe03065340261572f016a2c47ed0"

ADMIN_IDS = [8227188993, 8655650754, 7705672932] 
ID_ANONIM = 1087968824 
GRUP_RESMI = [-1003760170878, -1003839747899, -1003588375021, -1003767837442]
LAST_WELCOME_ID = {}
LOG_REQUESTS = {}

# --- [ FUNGSI PEMETAAN NEGARA ] ---
def get_nama_negara_lengkap(country_code):
    if not country_code: return "Tidak Diketahui"
    map_negara = {
        "US": "Amerika Serikat", "ID": "Indonesia", "KR": "Korea Selatan", 
        "JP": "Jepang", "CN": "Tiongkok", "TH": "Thailand", "GB": "Inggris", 
        "IN": "India", "RU": "Rusia", "FR": "Prancis", "DE": "Jerman", 
        "ES": "Spanyol", "IT": "Italia", "MY": "Malaysia", "SG": "Singapura",
        "PH": "Filipina", "VN": "Vietnam", "TR": "Turki", "BR": "Brasil",
        "CA": "Kanada", "AU": "Australia", "MX": "Meksiko"
    }
    return map_negara.get(country_code.upper(), country_code.upper())

# --- [ 2. INITIALIZATION ] ---
session = requests.Session()
retries = Retry(
    total=10, 
    backoff_factor=2, 
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)
session.headers.update({'User-Agent': "Vidio/5.94.1 (Android 13; Mobile; ID; 123456)"})

# Force timeout configuration for Telebot
apihelper.SESSION_TIME_OUT = 300
apihelper.CONNECT_TIMEOUT = 300
apihelper.READ_TIMEOUT = 300

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)
app = Flask(__name__)

@app.route('/')
def index_flask(): return "<b>PALU BASA SYSTEM ONLINE</b>"

logging.basicConfig(level=logging.INFO)
client_gemini = genai.Client(api_key=GEMINI_KEY)
groq_client = Groq(api_key=GROQ_KEY)

try:
    GLOBAL_BG = Image.open("bg.jpg").convert('RGB').resize((640, 480), Image.LANCZOS)
    FONT_PATH = "NotoSansJP.ttf"
    F_TITLE = ImageFont.truetype(FONT_PATH, 30)
    F_NAME = ImageFont.truetype(FONT_PATH, 34)
    F_GROUP = ImageFont.truetype(FONT_PATH, 25)
    F_WM = ImageFont.truetype(FONT_PATH, 14)
except:
    GLOBAL_BG = Image.new('RGB', (640, 480), color=(15, 15, 15))
    F_TITLE = F_NAME = F_GROUP = F_WM = ImageFont.load_default()

# --- [ 3. VISUAL GENERATOR ] ---
def buat_image_welcome(user_id, first_name, group_name):
    canvas = GLOBAL_BG.copy() 
    draw = ImageDraw.Draw(canvas)
    pfp_size = 200 
    pfp_x, pfp_y = 220, 30 
    
    try:
        photos = bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            file_info = bot.get_file(photos.photos[0][-1].file_id)
            pfp_resp = session.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}", timeout=20)
            if pfp_resp.status_code == 200:
                pfp = Image.open(io.BytesIO(pfp_resp.content)).convert("RGBA")
            else:
                raise Exception("Download Gagal")
        else:
            raise Exception("No PFP")
    except Exception as e:
        warna_dasar = [(255, 99, 71), (64, 224, 208), (135, 206, 250), (255, 215, 0)]
        pfp = Image.new('RGBA', (pfp_size, pfp_size), color=random.choice(warna_dasar))
        draw_pfp = ImageDraw.Draw(pfp)
        inisial = "".join([n[0] for n in first_name.split()[:2]]).upper()
        try: font_inisial = ImageFont.truetype(FONT_PATH, 90)
        except: font_inisial = ImageFont.load_default()
        l, t, r, b = draw_pfp.textbbox((0, 0), inisial, font=font_inisial)
        x_pos = (pfp_size - (r-l)) / 2
        y_pos = (pfp_size - (b-t)) / 2 - 15 
        draw_pfp.text((x_pos+3, y_pos+3), inisial, fill="black", font=font_inisial)
        draw_pfp.text((x_pos, y_pos), inisial, fill="white", font=font_inisial)

    pfp = pfp.resize((pfp_size, pfp_size), Image.LANCZOS)
    mask = Image.new('L', (pfp_size, pfp_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, pfp_size, pfp_size), fill=255)
    pfp.putalpha(mask)
    canvas.paste(pfp, (pfp_x, pfp_y), pfp)
    draw.ellipse((pfp_x, pfp_y, pfp_x + pfp_size, pfp_y + pfp_size), outline=(255, 215, 0), width=5)

    def draw_text_clear(draw_obj, teks, font, pos_y, fill_color="white", outline_color="black"):
        l, t, r, b = draw_obj.textbbox((0, 0), teks, font=font)
        x = 320 - ((r - l) / 2)
        for ox, oy in [(-2,-2), (2,2), (-2,2), (2,-2), (0,-2), (0,2), (-2,0), (2,0)]:
            draw_obj.text((x + ox, pos_y + oy), teks, fill=outline_color, font=font)
        draw_obj.text((x, pos_y), teks, fill=fill_color, font=font)

    start_y = pfp_y + pfp_size + 15 
    draw_text_clear(draw, "Selamat Datang!!!", F_TITLE, start_y)
    draw_text_clear(draw, first_name.upper(), F_NAME, start_y + 50)
    draw_text_clear(draw, f"di @SHeJUa", F_GROUP, start_y + 110)

    txt_wm = "Powered by @SHeJUa"
    l, t, r, b = draw.textbbox((0, 0), txt_wm, font=F_WM)
    xw, yw = (640 - (r-l) - 15), (480 - (b-t) - 15)
    for ox, oy in [(-1, -1), (1, 1), (-1, 1), (1, -1), (0, 1), (1, 0)]:
        draw.text((xw + ox, yw + oy), txt_wm, fill="black", font=F_WM)
    draw.text((xw, yw), txt_wm, fill="white", font=F_WM)

    img_byte_arr = io.BytesIO()
    canvas.save(img_byte_arr, format='JPEG', quality=90)
    img_byte_arr.seek(0)
    return img_byte_arr

# --- [ 4. DUAL ENGINE AI ] ---
def get_ai_response(prompt, user_name, user_id):
    sekarang = datetime.utcnow() + timedelta(hours=7)
    jam = sekarang.strftime("%H:%M")
    hari_indo = {"Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu", "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"}
    hari = hari_indo.get(sekarang.strftime("%A"), sekarang.strftime("%A"))
    salam = "Selamat Pagi" if 5 <= sekarang.hour < 12 else "Selamat Siang" if 12 <= sekarang.hour < 15 else "Selamat Sore" if 15 <= sekarang.hour < 18 else "Selamat Malam"

    if user_id in ADMIN_IDS or user_id == ID_ANONIM:
        instruksi = "Ini Mimin. Bicara manja dan panggil 'Mimin'. Dilarang panggil nama aslinya."
    else:
        instruksi = f"Panggil lawan bicaramu dengan sebutan 'KaK {user_name}'."

    aturan = f"Nama kamu Lusi, asisten ceria milik Mimin di @SHeJUa. INFO WAKTU: {jam}, {hari}. Salam: {salam}. {instruksi}"
    
    try:
        response = client_gemini.models.generate_content(model="gemini-2.0-flash", contents=f"{aturan}\n\nPesan: {prompt}")
        teks = response.text
    except:
        try:
            completion = groq_client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": aturan}, {"role": "user", "content": prompt}])
            teks = completion.choices[0].message.content
        except: teks = "Aduh maaf ya sayang, Lusi lagi SIBUK. Coba lagi nanti! 🎀"
    
    return teks.replace("bot", "Lusi").replace("Bot", "Lusi")

# --- [ 5. IMDB & DETAIL SYSTEM ] ---
def draw_watermark_poster(input_bytes, wm_text):
    try:
        poster = Image.open(input_bytes).convert("RGB")
        w, h = poster.size
        wm_overlay = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(wm_overlay)
        font_size = max(int(h * 0.035), 22)
        try: font = ImageFont.truetype(FONT_PATH, font_size)
        except: font = ImageFont.load_default()
        l, t, r, b = draw.textbbox((0, 0), wm_text, font=font)
        x, y = w - (r-l) - 20, h - (b-t) - 20
        for ax in range(-2, 3):
            for ay in range(-2, 3): draw.text((x+ax, y+ay), wm_text, fill=(0, 0, 0, 230), font=font)
        draw.text((x, y), wm_text, fill=(255, 255, 0, 255), font=font)
        combined = Image.alpha_composite(poster.convert('RGBA'), wm_overlay).convert('RGB')
        out = io.BytesIO()
        combined.save(out, format='JPEG', quality=95); out.seek(0)
        return out
    except: return input_bytes

def fetch_results(chat_id, query, page=1, message_id=None, panggilan_user="{name}"):
    try:
        clean_query = query.strip()
        res = session.get("https://api.themoviedb.org/3/search/multi", params={"api_key": TMDB_KEY, "query": clean_query, "page": page, "language": "en-US"}).json()
        total_pages = res.get('total_pages', 1)
        results = [r for r in res.get('results', []) if r.get('media_type') in ['movie', 'tv']]
        if not results:
            bot.send_message(chat_id, f"<b>Pencarian tidak ditemukan {panggilan_user}. 🛡️</b>", parse_mode="HTML")
            return
        markup = types.InlineKeyboardMarkup()
        for r in results[:8]:
            t = (r.get('original_title' if r.get('original_language')=='id' else 'title') or r.get('name') or "Unknown").title()
            y = (r.get('release_date') or r.get('first_air_date') or "")[:4]
            markup.add(types.InlineKeyboardButton(f"{'🎬' if r.get('media_type')=='movie' else '📺'} {t} ({y or '?'})", callback_data=f"det_{r.get('media_type')}_{r['id']}"))
        p_p, n_p = (total_pages if page == 1 else page - 1), (1 if page == total_pages else page + 1)
        markup.row(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{clean_query}_{p_p}"), types.InlineKeyboardButton(f"🟢 {page}/{total_pages} 🟢", callback_data="none"), types.InlineKeyboardButton("Next ➡️", callback_data=f"page_{clean_query}_{n_p}"))
        markup.add(types.InlineKeyboardButton("❌ TUTUP ❌", callback_data="close"))
        teks = f"🔍 <b>Hasil Pencarian {panggilan_user}:</b> <code>{clean_query}</code>"
        if message_id: bot.edit_message_text(teks, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
        else: bot.send_message(chat_id, teks, reply_markup=markup, parse_mode="HTML")
    except Exception as e: logging.error(f"Error search: {e}")

def display_detail(message, m_type, m_id, user):
    try:
        res_id = session.get(f"https://api.themoviedb.org/3/{m_type}/{m_id}", params={"api_key": TMDB_KEY, "append_to_response": "credits", "language": "id-ID"}).json()
        res_en = session.get(f"https://api.themoviedb.org/3/{m_type}/{m_id}", params={"api_key": TMDB_KEY, "append_to_response": "credits", "language": "en-US"}).json()
        
        main_link = "https://t.me/SHeJUa"
        def bl(txt): return f"<b><a href='{main_link}'>{txt}</a></b>"
        def bd(txt): return f"<b>{txt}</b>"

        def lusi_translate(text):
            try:
                url = f"https://api.mymemory.translated.net/get?q={text[:500]}&langpair=en|id"
                resp = requests.get(url, timeout=3).json()
                return resp['responseData']['translatedText']
            except: return text

        def format_tgl_indo(tgl_str):
            if not tgl_str: return None
            try:
                bln_id = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
                dt = datetime.strptime(tgl_str, '%Y-%m-%d')
                return f"{dt.day} {bln_id[dt.month-1]} {dt.year}"
            except: return tgl_str

        title = (res_id.get('title') or res_id.get('name') or res_en.get('title') or "Unknown").title()
        year = (res_en.get('release_date') or res_en.get('first_air_date') or "0000")[:4]
        ori_title = res_id.get('original_title') or res_id.get('original_name') or ""
        
        caption = f"{bl(f'{title} ({year})')}\n"
        tipe = '🎬 MOVIE' if m_type == 'movie' else '📺 SERIES'
        if ori_title and ori_title.lower() != title.lower():
            caption += f"🏷️ {bd('Tipe:')} {bl(tipe)} | {bd('AKA:')} {bl(ori_title)}\n"
        else:
            caption += f"🏷️ {bd('Tipe:')} {bl(tipe)}\n"
            
        tagline = res_id.get('tagline') or res_en.get('tagline')
        if tagline: caption += f"📢 <i>{bl(f'“{tagline}”')}</i>\n"

        caption += f"📍 {bd('Tempat Nonton:')} {bl('Silakan Request Mimin')}\n"
        caption += "━━━━━━━━━━━━━━━━━━━━\n"

        tech = []
        if m_type == 'movie':
            run = res_id.get('runtime') or res_en.get('runtime')
            if run: tech.append(f"🕒 {bd('Durasi:')} {bl(f'{run} Menit')}")
        else:
            sns = res_id.get('number_of_seasons')
            eps = res_id.get('number_of_episodes')
            if sns: tech.append(f"🕒 {bd('Info:')} {bl(f'{sns} S | {eps} E')}")
        
        rate = res_id.get('vote_average', 0)
        if rate > 0: tech.append(f"🌟 {bd('Rating:')} {bl(f'{rate:.1f}/10')}")
        if tech: caption += " | ".join(tech) + "\n"

        tgl_raw = res_id.get('release_date') or res_id.get('first_air_date')
        tgl_indo = format_tgl_indo(tgl_raw)
        if tgl_indo: caption += f"📅 {bd('Rilis:')} {bl(tgl_indo)}\n"

        caption += f"🔞 {bd('Kategori:')} {bl('Dewasa (18+)' if res_id.get('adult') else 'Semua Umur / Remaja')}\n"
        
        c_code = (res_id.get('origin_country') or [""])[0]
        if c_code: caption += f"🌍 {bd('Negara:')} {bl(get_nama_negara_lengkap(c_code))}\n"

        studios = [bl(s['name']) for s in res_id.get('production_companies', [])]
        if studios: caption += f"🏢 {bd('Studio:')} {', '.join(studios[:2])}\n"

        genres = [bl(g['name']) for g in res_id.get('genres', [])]
        if genres: caption += f"🎭 {bd('Genre:')} {', '.join(genres[:3])}\n"

        creds = res_id.get('credits', {})
        dir_name = next((c['name'] for c in creds.get('crew', []) if c['job'] == 'Director'), None)
        cast = creds.get('cast', [])[:5]

        if dir_name or cast:
            caption += "━━━━━━━━━━━━━━━━━━━━\n"
            caption += f"🎬 {bd('Cast & Crew :')}\n"
            if dir_name: caption += f"👤 {bd('Sutradara:')} {bl(dir_name)}\n"
            if cast:
                c_list = [f"{bl(c['name'])} ({c['character']})" for c in cast]
                caption += f"👥 {bd('Pemeran:')} {', '.join(c_list)}\n"

        plot = res_id.get('overview')
        if not plot or plot.strip() == "":
            raw_plot = res_en.get('overview') or "Sinopsis belum tersedia."
            plot = lusi_translate(raw_plot)
        
        if len(plot) > 400: plot = plot[:397] + "..."
        
        caption += "━━━━━━━━━━━━━━━━━━━━\n"
        caption += f"📝 {bd('Plot:')}\n<blockquote>{html.escape(plot)}</blockquote>\n"
        
        is_prive = (user.id in ADMIN_IDS or user.id == ID_ANONIM or user.username == "GroupAnonymousBot")
        p_n = "Mimin" if is_prive else f"KaK {user.first_name}"
        caption += f"\n👤 {bd(f'Dicari oleh: {p_n}')} @SHeJUa 💎"

        img = res_id.get('backdrop_path') or res_id.get('poster_path')
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        
        try:
            raw_img = io.BytesIO(session.get(f"https://image.tmdb.org/t/p/w1280{img}", timeout=5).content)
            photo = draw_watermark_poster(raw_img, "Created by @SHeJUa")
        except:
            with open("bg.jpg", "rb") as f: photo = f.read()

        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🎬 Join Channel Utama 💎", url=main_link)).add(types.InlineKeyboardButton("🔹 CLOSE 🔒 🔹", callback_data="close"))
        bot.send_photo(message.chat.id, photo, caption=caption, parse_mode="HTML", reply_markup=markup)
        
    except Exception as e: 
        print(f"Error Detail: {e}")

# --- [ 6. LOGIKA LAPORAN MEMBER & JAPRI ] ---
def check_culik_report(m):
    u_id = m.from_user.id
    if m.chat.type == "private" and u_id not in ADMIN_IDS and u_id != ID_ANONIM and m.from_user.username != "GroupAnonymousBot":
        u_name = html.escape(m.from_user.first_name)
        pesan = (f"🚨 <b>LAPORAN JAPRI (CULIK)</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                 f"👤 <b>User:</b> <a href='tg://user?id={u_id}'>{u_name}</a>\n🆔 <b>ID:</b> <code>{u_id}</code>\n"
                 f"💬 <b>Pesan:</b> <code>{m.text}</code>\n━━━━━━━━━━━━━━━━━━━━")
        for aid in ADMIN_IDS:
            try: bot.send_message(aid, pesan, parse_mode="HTML")
            except: pass

@bot.chat_member_handler(func=lambda m: m.new_chat_member.status in ['left', 'kicked'])
def handle_member_left(m):
    u = m.new_chat_member.user
    tgl = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%d %b %H:%M:%S ZAN')
    laporan = (f"🏃 <b>MEMBER TELAH KELUAR</b>\n━━━━━━━━━━━━━━━━━━━━\n"
               f"👤 <b>User:</b> <a href='tg://user?id={u.id}'>{html.escape(u.first_name)}</a>\n"
               f"🏢 <b>Grup:</b> {html.escape(m.chat.title)}\n📍 <b>Aksi:</b> {m.new_chat_member.status.upper()}\n"
               f"📅 <b>Waktu:</b> {tgl}\n━━━━━━━━━━━━━━━━━━━━")
    for aid in ADMIN_IDS:
        try: bot.send_message(aid, laporan, parse_mode="HTML")
        except: pass

@bot.chat_member_handler(func=lambda m: m.new_chat_member.status == 'member')
def handle_new_member_join(m):
    if m.old_chat_member.status not in ['left', 'kicked', 'none']: return
    u = m.new_chat_member.user
    u_id = u.id
    g_id = m.chat.id
    g_name = m.chat.title
    tgl = datetime.now(pytz.timezone('Asia/Jakarta')).strftime('%d %b %H:%M:%S ZAN')
    link_info = f"🔗 {m.invite_link.name}" if m.invite_link else "🔍 Manual/Username"
    
    laporan = (f"🆕 <b>MEMBER BARU BERGABUNG</b>\n━━━━━━━━━━━━━━━━━━━━\n"
               f"👤 <b>Dari:</b> <a href='tg://user?id={u_id}'>{html.escape(u.first_name)}</a>\n"
               f"🏢 <b>Grup:</b> {html.escape(g_name)}\n🔗 <b>Tautan:</b> {link_info}\n"
               f"📅 <b>Tanggal:</b> {tgl}\n━━━━━━━━━━━━━━━━━━━━")
    for aid in ADMIN_IDS:
        try: bot.send_message(aid, laporan, parse_mode="HTML")
        except: pass
    
    send_welcome_banner(g_id, u, g_name)

# --- [ 7. WELCOME HANDLER ] ---
def send_welcome_banner(chat_id, user, chat_title):
    global LAST_WELCOME_ID
    panggilan = "Mimin" if (user.id in ADMIN_IDS or user.id == ID_ANONIM) else f"KaK {user.first_name}"
    
    if chat_id in LAST_WELCOME_ID:
        try: bot.delete_message(chat_id, LAST_WELCOME_ID[chat_id])
        except: pass

    caption = (f"<b>Hai {panggilan}! 🎀 Selamat bergabung di {chat_title}!</b>\n\n"
                f"🔍 <b>Cari Film:</b> Ketik <code>!s judul</code>\n"
                f"🎬 <b>Cek Detail:</b> <code>/imdb judul</code>\n"
                f"🍿 <b>Rikues:</b> <code>#request judul + tahun</code>\n\n"
                f"<b>Semoga betah ya, salam dari Lusi & Mimin! 🌸✨</b>")
    
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📢 GABUNG CHANNEL", url="https://t.me/SheJua"))
    try:
        img = buat_image_welcome(user.id, user.first_name, chat_title)
        sent = bot.send_photo(chat_id, img, caption=caption, parse_mode="HTML", reply_markup=markup)
        LAST_WELCOME_ID[chat_id] = sent.message_id
    except:
        sent = bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=markup)
        LAST_WELCOME_ID[chat_id] = sent.message_id

@bot.message_handler(content_types=['new_chat_members'])
@bot.chat_join_request_handler()
def handle_welcome_universal(m):
    users = m.new_chat_members if hasattr(m, 'new_chat_members') else [m.from_user]
    if hasattr(m, 'chat'):
        for u in users:
            if u.id == bot.get_me().id: continue
            send_welcome_banner(m.chat.id, u, m.chat.title)
            if not hasattr(m, 'new_chat_members'):
                bot.approve_chat_join_request(m.chat.id, u.id)

# --- [ 8. MAIN HANDLERS ] ---
def simpan_ke_index(judul, chat_id, message_id, thread_id=None):
    if not judul: return False
    judul_clean = judul.split('\n')[0]
    judul_clean = re.sub(r'^\[.*?\]\s*', '', judul_clean).strip()
    judul_clean = re.sub(r'^(Judul:|File:)', '', judul_clean, flags=re.IGNORECASE).strip()
    judul_clean = re.sub(r'<.*?>|http\S+|t\.me\S+', '', judul_clean)
    judul_clean = judul_clean.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    judul_clean = re.sub(r'\.(mp4|mkv|avi|zip|rar)$', '', judul_clean, flags=re.IGNORECASE)
    judul_clean = re.sub(r'\s+', ' ', judul_clean).strip().lower()
    if not judul_clean: return False
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            if f"{chat_id} | {message_id}" in f.read(): return False
    entry = f"{judul_clean} | {chat_id} | {message_id} | {thread_id or ''}\n"
    with open(INDEX_FILE, "a", encoding="utf-8") as f: f.write(entry)
    return True

@bot.message_handler(content_types=['video', 'document'])
def handle_incoming_video(m):
    is_video = m.content_type == 'video' or (m.content_type == 'document' and m.document.mime_type and "video" in m.document.mime_type)
    if is_video and m.caption:
        if simpan_ke_index(m.caption, m.chat.id, m.message_id, m.message_thread_id if m.is_topic_message else None): sync_ke_cloud()

@bot.message_handler(commands=['scrapemasal'])
def scrape_masal_handler(m):
    if m.from_user.id not in ADMIN_IDS: return
    limit = int(m.text.split()[1]) if len(m.text.split()) > 1 else 100
    notif = bot.reply_to(m, f"🚀 <b>Menyisir {limit} pesan...</b>", parse_mode="HTML")
    def worker():
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        sync_ke_cloud()
        bot.edit_message_text(f"✅ <b>Selesai!</b>", m.chat.id, notif.message_id, parse_mode="HTML")
    Thread(target=worker).start()

@bot.message_handler(commands=['imdb'])
def handle_imdb_command(m):
    panggilan = "Mimin" if (m.from_user.id in ADMIN_IDS or m.from_user.id == ID_ANONIM) else f"KaK {m.from_user.first_name}"
    query = m.text.replace("/imdb", "").strip()
    if not query: bot.reply_to(m, f"<b>Judulnya mana {panggilan}? 🌸</b>", parse_mode="HTML"); return
    fetch_results(m.chat.id, query, panggilan_user=panggilan)

@bot.message_handler(func=lambda m: True)
def handle_messages(m):
    if not m.text: return
    text_raw = m.text; text_lower = text_raw.lower()
    u_id = m.from_user.id
    panggilan = "Mimin" if (u_id in ADMIN_IDS or u_id == ID_ANONIM or m.from_user.username == "GroupAnonymousBot") else f"KaK {m.from_user.first_name}"
    
    check_culik_report(m)

    if "#request" in text_lower or "rikues" in text_lower:
        has_tag = "#request" in text_lower
        has_year = re.search(r'\b(19|20)\d{2}\b', text_raw)
        if not has_tag or not has_year:
            if u_id not in ADMIN_IDS:
                bot.reply_to(m, f"<b>Aduh {panggilan}, format salah! Contoh: #request Lucy (2014)</b> 🎀", parse_mode="HTML")
                return
        else:
            bot.reply_to(m, f"<b>Sip {panggilan}, sudah Lusi laporin ke Mimin! 🎬</b>", parse_mode="HTML")
            req_id = f"{m.chat.id}_{m.message_id}"
            LOG_REQUESTS[req_id] = []
            laporan = (f"📢 <b>LAPORAN REQUEST</b>\n━━━━━━━━━━━━━━━━━━━━\n👤 <b>Peminta:</b> {panggilan}\n🎬 <b>Judul:</b> <code>{text_raw}</code>\n📍 <b>Status:</b> Menunggu\n━━━━━━━━━━━━━━━━━━━━")
            markup = types.InlineKeyboardMarkup()
            markup.row(types.InlineKeyboardButton("✅ UPLOADED", callback_data=f"up_{req_id}"), types.InlineKeyboardButton("💎 VIP", callback_data=f"vip_{req_id}"))
            markup.row(types.InlineKeyboardButton("📂 KOSONG", callback_data=f"ada_{req_id}"), types.InlineKeyboardButton("⏳ PROSES", callback_data=f"proses_{req_id}"))
            for aid in ADMIN_IDS:
                msg = bot.send_message(aid, laporan, reply_markup=markup, parse_mode="HTML")
                LOG_REQUESTS[req_id].append({"aid": aid, "mid": msg.message_id, "text": laporan})
            return

    if text_lower.startswith('!s '):
        query = text_lower[3:].strip()
        hasil = []
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    data = line.strip().split(' | ')
                    if len(data) >= 3 and query in data[0]: 
                        hasil.append(data)
        
        if hasil:
            res_txt = f"<b>Daftar pencarian {panggilan}</b>\n"
            for i, h in enumerate(hasil[:10], 1):
                clean_chat_id = h[1].replace('-100', '')
                link = f"https://t.me/c/{clean_chat_id}/{h[2]}"
                res_txt += f"👉<b>{i}. <a href='{link}'>{h[0].upper()}</a></b>\n"
            bot.reply_to(m, res_txt, parse_mode="HTML", disable_web_page_preview=True)
        else: 
            bot.reply_to(m, f"<b>Belum ada {panggilan}, rikues aja ya! 🌸</b>", parse_mode="HTML")
        return

    is_reply = m.reply_to_message and m.reply_to_message.from_user.id == bot.get_me().id
    if "lusi" in text_lower or is_reply or (m.chat.type == "private"):
        bot.reply_to(m, get_ai_response(text_raw, m.from_user.first_name, u_id), parse_mode="HTML")

# --- [ 9. FUNGSI CALLBACK & STATUS ] ---
@bot.callback_query_handler(func=lambda c: True)
def handle_callbacks(c):
    d = c.data.split('_')
    if d[0] in ["up", "vip", "ada", "proses"]:
        if c.from_user.id not in ADMIN_IDS: return
        req_id = f"{d[1]}_{d[2]}"
        mapping = {
            "up": ("✅ SUDAH DIUPLOAD", "🎬 Sudah di-upload, silakan dicek"), 
            "vip": ("💎 KHUSUS VIP", "💎 Tersedia untuk Member VIP"), 
            "ada": ("📂 BELUM ADA", "📂 Belum tersedia saat ini."), 
            "proses": ("⏳ PROSES", "⏳ Sedang diproses, harap bersabar")
        }
        status, notif = mapping[d[0]]
        
        if d[0] != "proses":
            if req_id in LOG_REQUESTS:
                for log in LOG_REQUESTS[req_id]:
                    try: 
                        teks_baru = re.sub(r'📌 <b>STATUS:</b>.*', '', log['text'], flags=re.DOTALL)
                        bot.edit_message_text(f"{teks_baru.strip()}\n📌 <b>STATUS:</b> {status}", log['aid'], log['mid'], parse_mode="HTML")
                    except: pass
        
        try: bot.send_message(d[1], f"<b>{notif}</b>", reply_to_message_id=int(d[2]), parse_mode="HTML")
        except: pass
        
    elif d[0] == "page": 
        fetch_results(c.message.chat.id, d[1], int(d[2]), c.message.message_id)
    elif d[0] == "det": 
        display_detail(c.message, d[1], d[2], c.from_user)
    elif d[0] == "close": 
        try: bot.delete_message(c.message.chat.id, c.message.message_id)
        except: pass

# --- [ 9. MAIN EXECUTION & STABILITY PATCH ] ---
if __name__ == "__main__":
    try: download_index()
    except: pass
    
    def run_flask():
        try:
            app.run(host='0.0.0.0', port=7860)
        except:
            print("⚠️ Port 7860 sibuk, Flask sudah jalan/perlu di-restart.")
    
    Thread(target=run_flask, daemon=True).start()
    
    print("🚀 Bot Lusi siap melayani Kak Mimin (Mode Bypass & High-Stability)!")
    
    try: bot.remove_webhook()
    except: pass
    
    while True:
        try:
            print("🚀 Lusi mencoba terhubung ke Telegram...")
            bot.infinity_polling(
                timeout=300, 
                long_polling_timeout=300,
                allowed_updates=telebot.util.update_types
            )
        except Exception as e:
            print(f"⚠️ Koneksi terputus: {e}. Melakukan pemulihan dalam 10 detik.")
            time.sleep(10)