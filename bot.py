import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes,
)
from data import LISTINGS
from filters import apply_filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MANAGER_TG = "@mary_eeee"
MANAGER_PHONE = "+7 (903) 157-05-47"


def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏢 Все объекты", callback_data="browse_all")],
        [InlineKeyboardButton("🔍 Подобрать по фильтрам", callback_data="filter_start")],
        [InlineKeyboardButton("📞 Связаться с менеджером", callback_data="contact")],
    ])

def filter_deal_kb(selected):
    def mark(key, val):
        return "✅ " if selected.get(key) == val else ""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{mark('deal','rent')}🔑 Аренда", callback_data="deal_rent"),
         InlineKeyboardButton(f"{mark('deal','buy')}💰 Покупка", callback_data="deal_buy")],
        [InlineKeyboardButton("➡️ Далее", callback_data="filter_next_tenant")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
    ])

def filter_tenant_kb(selected):
    def mark(val):
        return "✅ " if selected.get("tenant") == val else ""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{mark('with')}🏪 С арендатором", callback_data="tenant_with"),
         InlineKeyboardButton(f"{mark('without')}🚪 Без арендатора", callback_data="tenant_without")],
        [InlineKeyboardButton(f"{mark('any')}🔄 Любой вариант", callback_data="tenant_any")],
        [InlineKeyboardButton("➡️ Далее", callback_data="filter_next_price")],
        [InlineKeyboardButton("◀️ Назад", callback_data="filter_start")],
    ])

def filter_price_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("до 500 000 руб", callback_data="price_0_500000"),
         InlineKeyboardButton("до 1 000 000 руб", callback_data="price_0_1000000")],
        [InlineKeyboardButton("до 3 000 000 руб", callback_data="price_0_3000000"),
         InlineKeyboardButton("до 5 000 000 руб", callback_data="price_0_5000000")],
        [InlineKeyboardButton("Любая цена", callback_data="price_any")],
        [InlineKeyboardButton("◀️ Назад", callback_data="filter_next_tenant")],
    ])

def listings_kb(listings, page=0):
    PAGE_SIZE = 5
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = listings[start:end]
    rows = []
    for item in chunk:
        label = f"{item['emoji']} {item['title']} — {fmt_price(item)}"
        rows.append([InlineKeyboardButton(label, callback_data=f"item_{item['id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"page_{page-1}"))
    total_pages = -(-len(listings) // PAGE_SIZE)
    nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
    if end < len(listings):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"page_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)

def item_kb(item_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Узнать подробнее", callback_data=f"request_{item_id}")],
        [InlineKeyboardButton("◀️ К списку", callback_data="browse_all"),
         InlineKeyboardButton("🏠 Меню", callback_data="main_menu")],
    ])

def fmt_price(item):
    p = item["price"]
    if item["deal"] == "rent":
        return f"{p:,} руб/мес".replace(",", " ")
    return f"{p:,} руб".replace(",", " ")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    text = (
        "👋 Добро пожаловать в каталог помещений и готовых арендных бизнесов!\n\n"
        "Здесь вы найдёте:\n"
        "🏢 Помещения — в аренду и на продажу\n"
        "🏪 Готовый бизнес — объекты с действующими арендаторами\n\n"
        "Выберите действие:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_kb())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_kb())


async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "noop":
        return
    if data == "main_menu":
        await start(update, ctx)
        return
    if data == "contact":
        await q.edit_message_text(
            f"📞 Свяжитесь с нашим менеджером:\n\nTelegram: {MANAGER_TG}\nТелефон: {MANAGER_PHONE}\n\nОтветим в течение 30 минут 🕐",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
        return
    if data == "browse_all":
        ctx.user_data["active_listings"] = LISTINGS
        ctx.user_data["page"] = 0
        await show_listings(q, LISTINGS, 0)
        return
    if data.startswith("page_"):
        page = int(data.split("_")[1])
        ctx.user_data["page"] = page
        listings = ctx.user_data.get("active_listings", LISTINGS)
        await show_listings(q, listings, page)
        return
    if data == "filter_start":
        ctx.user_data["filters"] = {}
        await q.edit_message_text("🔍 Шаг 1 из 3 — Тип сделки\n\nЧто вас интересует?", reply_markup=filter_deal_kb({}))
        return
    if data in ("deal_rent", "deal_buy"):
        ctx.user_data.setdefault("filters", {})["deal"] = data.split("_")[1]
        await q.edit_message_text("🔍 Шаг 1 из 3 — Тип сделки\n\nЧто вас интересует?", reply_markup=filter_deal_kb(ctx.user_data["filters"]))
        return
    if data == "filter_next_tenant":
        await q.edit_message_text("🔍 Шаг 2 из 3 — Арендатор\n\nНужен объект с действующим арендатором?", reply_markup=filter_tenant_kb(ctx.user_data.get("filters", {})))
        return
    if data in ("tenant_with", "tenant_without", "tenant_any"):
        ctx.user_data.setdefault("filters", {})["tenant"] = data.split("_")[1]
        await q.edit_message_text("🔍 Шаг 2 из 3 — Арендатор\n\nНужен объект с действующим арендатором?", reply_markup=filter_tenant_kb(ctx.user_data["filters"]))
        return
    if data == "filter_next_price":
        await q.edit_message_text("🔍 Шаг 3 из 3 — Бюджет\n\nВыберите максимальную цену:", reply_markup=filter_price_kb())
        return
    if data.startswith("price_"):
        parts = data.split("_")
        if parts[1] == "any":
            ctx.user_data.setdefault("filters", {})["price_max"] = None
        else:
            ctx.user_data.setdefault("filters", {})["price_max"] = int(parts[2])
        results = apply_filters(LISTINGS, ctx.user_data.get("filters", {}))
        ctx.user_data["active_listings"] = results
        ctx.user_data["page"] = 0
        if not results:
            await q.edit_message_text(
                "😔 По вашим фильтрам ничего не найдено.\n\nПопробуйте изменить параметры.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Изменить фильтры", callback_data="filter_start")],
                    [InlineKeyboardButton("📋 Все объекты", callback_data="browse_all")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
                ])
            )
        else:
            await show_listings(q, results, 0, title=f"✅ Найдено {len(results)} объектов")
        return
    if data.startswith("item_"):
        item_id = int(data.split("_")[1])
        item = next((x for x in LISTINGS if x["id"] == item_id), None)
        if not item:
            return
        deal_label = "Аренда" if item["deal"] == "rent" else "Продажа"
        tenant_label = "✅ Есть арендатор" if item["tenant"] else "❌ Без арендатора"
        text = (
            f"{item['emoji']} {item['title']}\n\n"
            f"📍 {item['address']}\n"
            f"📐 Площадь: {item['area']} м2\n"
            f"🏷 Тип сделки: {deal_label}\n"
            f"👥 Арендатор: {tenant_label}\n"
            f"💰 Цена: {fmt_price(item)}\n\n"
            f"📝 {item['description']}"
        )
        await q.edit_message_text(text, reply_markup=item_kb(item_id))
        return
    if data.startswith("request_"):
        item_id = int(data.split("_")[1])
        item = next((x for x in LISTINGS if x["id"] == item_id), None)
        name = item["title"] if item else "объект"
        await q.edit_message_text(
            f"📩 Заявка на {name} отправлена!\n\nМенеджер свяжется с вами в ближайшее время.\n\nИли напишите сами: {MANAGER_TG}\nТелефон: {MANAGER_PHONE}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
        return


async def show_listings(q, listings, page, title="📋 Каталог объектов"):
    text = f"{title}\nВсего объектов: {len(listings)}\n\nВыберите объект:"
    await q.edit_message_text(text, reply_markup=listings_kb(listings, page))


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("Бот запущен!")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())



if __name__ == "__main__":
    main()
