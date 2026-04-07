import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ["TOKEN"]
API_KEY = os.environ["API_KEY"]

INTERVAL = 180
PROG_MOCNY = 90
PROG_DOBRY = 80

DOZWOLONE_LIGI = [
    "Eredivisie",
    "Bundesliga",
    "Premier League",
    "Serie A"
]

CHAT_ID = None
WYSLANE_ALERTY = set()


def ocen(m):
    punkty = 0
    max_punkty = 11
    powody = []

    if m["minuta"] >= 70:
        punkty += 2
        powody.append("końcówka meczu")

    if m["atk_celne"] >= 4:
        punkty += 2
        powody.append("dużo celnych strzałów")

    if m["atk_cisnienie"] >= 8:
        punkty += 2
        powody.append("wysokie ciśnienie")

    if m["atk_celne"] - m["def_celne"] >= 2:
        punkty += 2
        powody.append("duża przewaga jednej strony")

    if m["wynik"] == "1-1":
        punkty += 2
        powody.append("mecz otwarty")

    return punkty, max_punkty, powody


def pobierz_mecze():
    url = "https://v3.football.api-sports.io/fixtures"

    headers = {
        "x-apisports-key": API_KEY
    }

    params = {
        "live": "all"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
    except Exception:
        return []

    mecze = []

    for m in data.get("response", []):
        try:
            liga = m["league"]["name"]

            if liga not in DOZWOLONE_LIGI:
                continue

            mecze.append({
                "mecz": f"{m['teams']['home']['name']} vs {m['teams']['away']['name']}",
                "minuta": m["fixture"]["status"]["elapsed"] or 0,
                "wynik": f"{m['goals']['home']}-{m['goals']['away']}",
                "atk_celne": 3,
                "atk_cisnienie": 7,
                "def_celne": 1,
                "kurs": 1.80
            })

        except Exception:
            continue

    return mecze


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    CHAT_ID = update.effective_chat.id

    await update.message.reply_text(
        "🔥 BOT LIVE AKTYWNY\n\n"
        f"Ligi: {', '.join(DOZWOLONE_LIGI)}\n"
        f"🚨 mocny alert: {PROG_MOCNY}%+\n"
        f"⚠️ dobry alert: {PROG_DOBRY}%+\n"
        f"⏱ skanowanie: co {INTERVAL} s"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot działa.")


async def skaner(context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID, WYSLANE_ALERTY

    if not CHAT_ID:
        return

    mecze = pobierz_mecze()

    for m in mecze:
        punkty, max_punkty, powody = ocen(m)
        procent = (punkty / max_punkty) * 100

        klucz = f"{m['mecz']}_{m['minuta']}_{m['wynik']}"

        if klucz in WYSLANE_ALERTY:
            continue

        if procent < PROG_DOBRY:
            continue

        tekst_powody = "\n".join([f"• {p}" for p in powody])

        if procent >= PROG_MOCNY:
            naglowek = "🚨 MOCNY ALERT GOLA ⚽🔥"
        else:
            naglowek = "⚠️ DOBRY ALERT GOLA ⚽"

        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=(
                f"{naglowek}\n\n"
                f"🏆 Mecz: {m['mecz']}\n"
                f"Minuta: {m['minuta']}\n"
                f"Wynik: {m['wynik']}\n"
                f"Punkty: {punkty}/{max_punkty} ({int(procent)}%)\n\n"
                f"Powody:\n{tekst_powody}"
            )
        )

        WYSLANE_ALERTY.add(klucz)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    app.job_queue.run_repeating(skaner, interval=INTERVAL, first=10)

    app.run_polling()


if __name__ == "__main__":
    main()
