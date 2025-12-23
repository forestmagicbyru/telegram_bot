import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8258645689:AAHjK3euSeF9-fMCZk5pIQWzWkdMzwUf70Q"
ADMIN_ID = 1912067480
PAY_LINK = "https://www.tinkoff.ru/rm/r_ebXOBATccZ.cSyxaKTqAZ/AcIWx94097"
DELIVERY_PRICE = 350

bot = Bot(TOKEN)
dp = Dispatcher()

# ================= ХРАНИЛИЩА =================
cart = {}
temp = {}
addresses = {}
awaiting_address = {}  # защита от случайных сообщений
orders = {}  # статус заказа: {'status': 'принят'/'отправлен'/'доставлен'}

# ================= ТОВАРЫ =================
PRODUCTS = {
    "panther": {"name": "🍄 Мухомор пантерный", "variants": {"10 г": 640, "50 г": 3200, "100 г": 6400}},
    "red": {"name": "🍄 Мухомор красный", "variants": {"50 г": 1320, "100 г": 2640}},
    "hericium": {"name": "🌿 Ежовик гребенчатый", "variants": {"50 г": 670, "100 г": 1340}},
    "caps_red": {"name": "💊 Капсулы красного 60 шт", "variants": {"1 уп.": 860}},
    "caps_panther": {"name": "💊 Капсулы пантерного 60 шт", "variants": {"1 уп.": 1980}},
    "promo": {
        "name": "🎁 Новогодний бум (набор)",
        "variants": {"Набор": 4200},
        "desc": "🎄 Новогоднее предназначение!\n\n• Капсулы пантерного 60 шт\n• Капсулы красного 180 шт\n• Шляпки пантерный 10 г + красный 10 г"
    }
}

# ================= СТАРТ =================
@dp.message(Command("start"))
async def start(message: types.Message):
    cart.setdefault(message.from_user.id, {})
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🛒 Корзина", callback_data="cart")],
        [InlineKeyboardButton(text="🎁 Акции", callback_data="promo")],
        [InlineKeyboardButton(text="🚚 Доставка", callback_data="delivery")],
        [InlineKeyboardButton(text="📊 Статус заказа", callback_data="status")]
    ])
    await message.answer(
        "👋 Добро пожаловать в наш магазин!\n\n"
        "Здесь вы можете приобрести качественные товары с быстрой доставкой.",
        reply_markup=kb
    )

# ================= ДОСТАВКА =================
@dp.callback_query(F.data == "delivery")
async def delivery(callback: types.CallbackQuery):
    await callback.message.answer(f"🚚 Фиксированная доставка — {DELIVERY_PRICE} ₽ (по цене такси)")

# ================= КАТАЛОГ =================
@dp.callback_query(F.data == "catalog")
async def catalog(callback: types.CallbackQuery):
    buttons = [[InlineKeyboardButton(text=p["name"], callback_data=f"prod:{k}")] for k, p in PRODUCTS.items()]
    buttons.append([InlineKeyboardButton(text="🏠 На главную", callback_data="home")])
    await callback.message.answer("📦 Каталог товаров:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ================= АКЦИИ =================
@dp.callback_query(F.data == "promo")
async def promo(callback: types.CallbackQuery):
    p = PRODUCTS["promo"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить в корзину", callback_data="prod:promo")],
        [InlineKeyboardButton(text="🏠 На главную", callback_data="home")]
    ])
    await callback.message.answer(p["desc"], reply_markup=kb)

# ================= ВЫБОР ТОВАРА =================
@dp.callback_query(F.data.startswith("prod:"))
async def product(callback: types.CallbackQuery):
    key = callback.data.split(":")[1]
    temp[callback.from_user.id] = {"product": key, "qty": 1}
    buttons = [[InlineKeyboardButton(text=f"{v} — {price} ₽", callback_data=f"var:{v}|{price}")] for v, price in PRODUCTS[key]["variants"].items()]
    await callback.message.answer(PRODUCTS[key]["name"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ================= ВАРИАНТ + КОЛ-ВО =================
@dp.callback_query(F.data.startswith("var:"))
async def variant(callback: types.CallbackQuery):
    user = callback.from_user.id
    variant, price = callback.data.replace("var:", "").split("|")
    temp[user]["variant"] = variant
    temp[user]["price"] = int(price)
    await show_qty(callback)

async def show_qty(callback):
    user = callback.from_user.id
    qty = temp[user]["qty"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➖", callback_data="qty:-"),
         InlineKeyboardButton(text=f"x{qty}", callback_data="noop"),
         InlineKeyboardButton(text="➕", callback_data="qty:+")],
        [InlineKeyboardButton(text="✅ Добавить в корзину", callback_data="add")],
        [InlineKeyboardButton(text="📦 В каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🏠 На главную", callback_data="home")]
    ])
    try:
        await callback.message.edit_text("Выберите количество:", reply_markup=kb)
    except:
        await callback.message.answer("Выберите количество:", reply_markup=kb)

@dp.callback_query(F.data.startswith("qty:"))
async def qty(callback: types.CallbackQuery):
    user = callback.from_user.id
    if callback.data == "qty:+": 
        temp[user]["qty"] += 1
    elif callback.data == "qty:-" and temp[user]["qty"] > 1:
        temp[user]["qty"] -= 1
    await update_qty(callback)

async def update_qty(callback):
    user = callback.from_user.id
    qty = temp[user]["qty"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➖", callback_data="qty:-"),
         InlineKeyboardButton(text=f"x{qty}", callback_data="noop"),
         InlineKeyboardButton(text="➕", callback_data="qty:+")],
        [InlineKeyboardButton(text="✅ Добавить в корзину", callback_data="add")],
        [InlineKeyboardButton(text="📦 В каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🏠 На главную", callback_data="home")]
    ])
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()

# ================= ДОБАВИТЬ В КОРЗИНУ =================
@dp.callback_query(F.data == "add")
async def add_to_cart(callback: types.CallbackQuery):
    user = callback.from_user.id
    t = temp[user]
    name = f"{PRODUCTS[t['product']]['name']} ({t['variant']})"
    if name in cart[user]:
        cart[user][name]["qty"] += t["qty"]
    else:
        cart[user][name] = {"qty": t["qty"], "price": t["price"]}
    await callback.message.answer("✅ Товар добавлен в корзину")

# ================= КОРЗИНА =================
@dp.callback_query(F.data == "cart")
async def show_cart(callback: types.CallbackQuery):
    user = callback.from_user.id
    if not cart[user]:
        await callback.message.answer("🛒 Корзина пуста")
        return
    total = DELIVERY_PRICE
    text = "🛒 Корзина:\n\n"
    buttons = []
    for i, (name, item) in enumerate(cart[user].items()):
        cost = item["qty"] * item["price"]
        total += cost
        text += f"{name} × {item['qty']} = {cost} ₽\n"
        buttons.append([
            InlineKeyboardButton(text="➖", callback_data=f"cart_qty:-:{i}"),
            InlineKeyboardButton(text=f"x{item['qty']}", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_qty:+:{i}"),
            InlineKeyboardButton(text="❌", callback_data=f"del:{i}")
        ])
    text += f"\n🚚 Доставка: {DELIVERY_PRICE} ₽"
    text += f"\n💰 Итого: {total} ₽"
    # Кнопка оплаты направляет на ввод адреса
    buttons.append([InlineKeyboardButton(text="💳 Оплатить", callback_data="address")])
    buttons.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart")])
    buttons.append([InlineKeyboardButton(text="📦 В каталог", callback_data="catalog")])
    buttons.append([InlineKeyboardButton(text="🏠 На главную", callback_data="home")])
    await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ================= РЕДАКТИРОВАНИЕ КОЛИЧЕСТВА В КОРЗИНЕ =================
@dp.callback_query(F.data.startswith("cart_qty:"))
async def cart_qty(callback: types.CallbackQuery):
    user = callback.from_user.id
    _, qty_action, index_str = callback.data.split(":")
    index = int(index_str)
    key = list(cart[user].keys())[index]
    if qty_action == "+":
        cart[user][key]["qty"] += 1
    elif qty_action == "-" and cart[user][key]["qty"] > 1:
        cart[user][key]["qty"] -= 1
    await show_cart(callback)

# ================= ОЧИСТКА КОРЗИНЫ =================
@dp.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    user = callback.from_user.id
    cart[user] = {}
    await callback.message.answer("Корзина очищена")
    await show_cart(callback)

# ================= УДАЛЕНИЕ ТОВАРА =================
@dp.callback_query(F.data.startswith("del:"))
async def delete_item(callback: types.CallbackQuery):
    user = callback.from_user.id
    index = int(callback.data.split(":")[1])
    key = list(cart[user].keys())[index]
    del cart[user][key]
    await callback.message.answer("❌ Товар удалён из корзины")
    await show_cart(callback)

# ================= АДРЕС =================
@dp.callback_query(F.data == "address")
async def ask_address(callback: types.CallbackQuery):
    user = callback.from_user.id
    awaiting_address[user] = True
    await callback.message.answer("Введите адрес доставки:")

@dp.message()
async def save_address(message: types.Message):
    user = message.from_user.id
    if not awaiting_address.get(user):
        await message.answer("Пожалуйста, используйте кнопки меню.")
        return
    addresses[user] = message.text
    awaiting_address[user] = False
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_address")],
        [InlineKeyboardButton(text="✏️ Изменить", callback_data="address")]
    ])
    await message.answer(f"Ваш адрес: {message.text}\nПодтверждаете?", reply_markup=kb)

@dp.callback_query(F.data == "confirm_address")
async def confirm_address(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", callback_data="pay")]
    ])
    await callback.message.answer("Адрес подтверждён!", reply_markup=kb)

# ================= ОПЛАТА =================
@dp.callback_query(F.data == "pay")
async def pay(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Перейти к оплате", url=PAY_LINK)],
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="paid")]
    ])
    await callback.message.answer("Оплатите заказ:", reply_markup=kb)

# ================= ОПЛАТИЛ =================
@dp.callback_query(F.data == "paid")
async def paid(callback: types.CallbackQuery):
    user = callback.from_user.id
    total = DELIVERY_PRICE
    text = "📦 НОВЫЙ ЗАКАЗ\n\n"
    # Информация о клиенте
    text += f"👤 {callback.from_user.full_name}\n"
    text += f"🆔 {callback.from_user.id}\n"
    text += f"📍 Адрес: {addresses.get(user)}\n\n"
    # Список товаров
    for name, item in cart[user].items():
        cost = item["qty"] * item["price"]
        total += cost
        text += f"{name} × {item['qty']} = {cost} ₽\n"
    text += f"\n🚚 Доставка: {DELIVERY_PRICE} ₽"
    text += f"\n💰 Итого: {total} ₽"
    # Отправка админу
    await bot.send_message(ADMIN_ID, text)
    orders[user] = {'status': 'принят'}
    # Сообщение клиенту
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 На главную", callback_data="home")]
    ])
    await callback.message.answer("Спасибо за оплату! Менеджер скоро с вами свяжется.", reply_markup=kb)

# ================= СТАТУС ЗАКАЗА =================
@dp.callback_query(F.data == "status")
async def status(callback: types.CallbackQuery):
    user = callback.from_user.id
    status = orders.get(user, {}).get('status', 'Нет заказов')
    await callback.message.answer(f"Статус вашего заказа: {status}")

# ================= НА ГЛАВНУЮ =================
@dp.callback_query(F.data == "home")
async def home(callback: types.CallbackQuery):
    await start(callback.message)

# ================= ЗАПУСК =================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())