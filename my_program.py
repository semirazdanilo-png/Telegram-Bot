import telebot
import urllib.request
import urllib.parse
import json
import ssl
from datetime import datetime
from telebot import types

# Твій токен Telegram
TOKEN = '8677157299:AAF0NGNEcddtbL8fre44-Rxccce7Wl8cuCE'
bot = telebot.TeleBot(TOKEN)

# Назви місяців для кнопок
MONTHS_NAMES = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня"
}

# Коди дощу
RAIN_CODES = {
    51: "очікується легка мряка", 53: "очікується помірна мряка", 55: "очікується густа мряка",
    61: "очікується невеликий дощ", 63: "очікується помірний дощ", 65: "очікується сильний дощ",
    80: "очікуються короткочасні дощі", 81: "очікується сильна злива", 
    82: "очікується потужна злива з грозою", 95: "очікується гроза з дощем"
}

def get_weather_data():
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    params = {
        "latitude": "49.8383",
        "longitude": "24.0232",
        "hourly": ["temperature_2m", "weathercode"],
        "timezone": "Europe/Kyiv"
    }
    
    full_url = f"{base_url}?{urllib.parse.urlencode(params, doseq=True)}"
    
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=context, timeout=10) as response:
            if response.status == 200:
                html = response.read().decode('utf-8')
                return json.loads(html)
    except Exception as e:
        print("Помилка отримання погоди:", e)
    return None
@bot.message_handler(commands=['start', 'weather'])
def send_welcome(message):
    chat_id = message.chat.id
    data = get_weather_data()
    
    if not data or 'hourly' not in data:
        bot.send_message(chat_id, "Привіт! Я бот Данила. Не вдалося оновити дані про погоду.")
        return

    markup = types.InlineKeyboardMarkup()
    current_date = datetime.now().date()

    unique_dates = []
    for time_str in data['hourly']['time']:
        date_part = time_str.split("T")[0]
        if date_part not in unique_dates:
            unique_dates.append(date_part)

    for date_str in unique_dates:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        if dt >= current_date:
            button_text = f"{dt.day} {MONTHS_NAMES[dt.month]}"
            callback_value = f"day_{date_str}"
            
            button = types.InlineKeyboardButton(text=button_text, callback_data=callback_value)
            markup.add(button)
            
    welcome_text = (
        "Привіт! Я бот Данила.\n"
        "На яку дату вам потрібна погода у Львові?\n"
        "Оберіть дату зі списку кнопок нижче (вони оновлюються автоматично):"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('day_'))
def handle_button_click(call):
    chat_id = call.message.chat.id
    target_date_str = call.data.replace("day_", "")
    target_dt = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    
    data = get_weather_data()
    
    if not data or 'hourly' not in data:
        bot.send_message(chat_id, "Помилка завантаження свіжих даних. Спробуйте пізніше.")
        return

    day_temperatures = []
    day_hours = []
    day_codes = []
    
    now = datetime.now()
    current_hour = now.hour
    is_today = (target_dt == now.date())

    current_hour_temp = None

    for idx, time_str in enumerate(data['hourly']['time']):
        time_str_clean = time_str.replace("T", " ")
        dt = datetime.strptime(time_str_clean, "%Y-%m-%d %H:%M")
        
        if dt.date() == target_dt:
            temp_value = data['hourly']['temperature_2m'][idx]
            day_temperatures.append(temp_value)
            day_hours.append(dt.hour)
            day_codes.append(data['hourly']['weathercode'][idx])
            
            if is_today and dt.hour == current_hour:
                current_hour_temp = temp_value

    if not day_temperatures:
        bot.send_message(chat_id, "На жаль, на цю дату прогнозу немає. Натисніть /start заново.")
        return

    max_temp = max(day_temperatures)
    min_temp = min(day_temperatures)

    max_hours = [day_hours[i] for i, t in enumerate(day_temperatures) if t == max_temp]
    min_hours = [day_hours[i] for i, t in enumerate(day_temperatures) if t == min_temp]

    max_time_str = f"з {min(max_hours)}:00 до {max(max_hours) + 1}:00"
    min_time_str = f"з {min(min_hours)}:00 до {max(min_hours) + 1}:00"

    rain_description = "дощу не очікується, буде сухо"
    for code in day_codes:
        if code in RAIN_CODES:
            rain_description = RAIN_CODES[code]
            break

    month_text = MONTHS_NAMES[target_dt.month]
    
    if is_today and current_hour_temp is not None:
        current_temp_line = f"Зараз у Львові на {current_hour}:00: {round(current_hour_temp)} градусів\n"
    else:
        current_temp_line = f"Прогноз на майбутню дату\n"

    weather_report = (
        f"{current_temp_line}"
        f"Прогноз погоди у Львові на {target_dt.day} {month_text}:\n\n"
        f"Максимальна температура: {round(max_temp)} градусів (буде {max_time_str})\n"
        f"Мінімальна температура: {round(min_temp)} градусів (буде {min_time_str})\n\n"
        f"Інформація про опади: {rain_description}.\n\n"
        f"Дані оновлено в момент вашого запиту."
    )
    
    bot.send_message(chat_id, weather_report)
    bot.answer_callback_query(call.id)

import os
import threading
from flask import Flask

app = Flask('')


@app.route("/")
def home():
    return "Бот працює!"


def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


# ЗАПУСК
threading.Thread(target=run).start()
bot.infinity_polling()
