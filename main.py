import logging
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ID каналов для заявок
CHANNEL_URGENT = "-1003409869914"
CHANNEL_REPAIR = "-1003435204867"  
CHANNEL_RENTAL = "-1003334937024"
CHANNEL_AUDIT = "-1003416208743"

# Состояния разговора
MAIN_MENU, URGENT_TYPE, URGENT_MODEL, URGENT_PROBLEM, URGENT_PHONE, URGENT_EMAIL, URGENT_INN = range(7)
REPAIR_TYPE, REPAIR_MODEL, REPAIR_PROBLEM, REPAIR_PHONE, REPAIR_EMAIL, REPAIR_INN = range(7, 13)
RENTAL_PURPOSE, RENTAL_TYPE, RENTAL_MODEL, RENTAL_PHONE, RENTAL_EMAIL, RENTAL_INN = range(13, 19)
AUDIT_PHONE, AUDIT_EMAIL, AUDIT_INN = range(19, 22)

# Разрешенное оборудование для срочной подмены
ALLOWED_EQUIPMENT = {
    'узи': ['узи', 'ультразвук', 'ультразвуковой'],
    'ивл': ['ивл', 'искусственная вентиляция легких', 'вентиляция легких'],
    'эндоскопия': ['эндоскопия', 'эндоскоп', 'гастроскоп', 'бронхоскоп', 'колоноскоп'],
    'нда': ['нда', 'наркозно дыхательный аппарат', 'анестезиологический', 'наркозный аппарат']
}

# Клавиатуры
main_menu_keyboard = [['⚡️ СРОЧНАЯ ПОДМЕНА ОБОРУДОВАНИЯ'], ['🔧 РЕМОНТ', '🧪 АРЕНДА ОБОРУДОВАНИЯ'], ['📊 БЕСПЛАТНЫЙ АУДИТ ОБОРУДОВАНИЯ']]
urgent_type_keyboard = [['УЗИ', 'ИВЛ'], ['Эндоскопия', 'НДА'], ['Другое', 'Назад']]
repair_type_keyboard = [['КТ', 'МРТ', 'Рентген'], ['УЗИ', 'ИВЛ', 'Эндоскопия'], ['НДА', 'Другое оборудование'], ['Назад']]
rental_purpose_keyboard = [['Тестирование нового направления'], ['Для лицензии'], ['Временная подмена'], ['Назад']]
back_only_keyboard = [['Назад']]
yes_no_keyboard = [['Да', 'Нет'], ['Назад']]
skip_keyboard = [['Пропустить'], ['Назад']]

def check_equipment_type(user_input):
    """Проверяет, является ли оборудование разрешенным для срочной подмены"""
    user_input = user_input.lower().strip()
    for main_type, variants in ALLOWED_EQUIPMENT.items():
        if any(variant in user_input for variant in variants):
            return main_type
    return None

def validate_inn(inn):
    """Проверяет валидность ИНН"""
    if not inn.isdigit():
        return False
    if len(inn) not in [10, 12]:
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_data.clear()
    await update.message.reply_text(
        '🏥 <b>Аварийная МедТехника</b>\n\n'
        '⚡️ Срочная подмена оборудования\n'
        '🔧 Ремонт любой сложности\n'
        '🧪 Аренда для развития клиники\n'
        '📊 Бесплатный аудит оборудования\n\n'
        'Решаем проблемы с оборудованием за 24 часа!\n\n'
        'Выберите нужную услугу:',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return MAIN_MENU

# ===== СРОЧНАЯ ПОДМЕНА =====
async def urgent_replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_data['service_type'] = 'urgent'
    await update.message.reply_text(
        '⚡️ <b>СРОЧНАЯ ПОДМЕНА ОБОРУДОВАНИЯ</b>\n\n'
        'Мы предоставляем подмену на время ремонта:\n• УЗИ\n• ИВЛ\n• Эндоскопия\n• НДА\n\n'
        'Выберите тип оборудования:',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(urgent_type_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return URGENT_TYPE

async def urgent_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Выберите услугу:', reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return MAIN_MENU
    if text == 'Другое':
        await update.message.reply_text('Укажите, какое именно оборудование вас интересует:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return URGENT_TYPE
    equipment_type = check_equipment_type(text)
    if equipment_type:
        user_data['equipment_type'] = equipment_type
        await update.message.reply_text('Введите модель аппарата:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return URGENT_MODEL
    else:
        if text not in ['УЗИ', 'ИВЛ', 'Эндоскопия', 'НДА']:
            await update.message.reply_text(
                f'К сожалению, мы не предоставляем срочную подмену для <b>{text}</b>. Но можем помочь с ремонтом или найти запчасти.\n\nХотите перейти в раздел ремонта?',
                parse_mode='HTML',
                reply_markup=ReplyKeyboardMarkup(yes_no_keyboard, one_time_keyboard=True)
            )
            return URGENT_TYPE
        else:
            user_data['equipment_type'] = text.lower()
            await update.message.reply_text('Введите модель аппарата:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
            return URGENT_MODEL

async def urgent_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Выберите тип оборудования:', reply_markup=ReplyKeyboardMarkup(urgent_type_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return URGENT_TYPE
    user_data['equipment_model'] = text
    await update.message.reply_text('Опишите проблему с оборудованием:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return URGENT_PROBLEM

async def urgent_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите модель аппарата:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return URGENT_MODEL
    user_data['problem_description'] = text
    await update.message.reply_text('Введите ваш телефон для связи:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return URGENT_PHONE

async def urgent_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Опишите проблему с оборудованием:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return URGENT_PROBLEM
    user_data['phone'] = text
    await update.message.reply_text('Введите ваш email:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return URGENT_EMAIL

async def urgent_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите ваш телефон для связи:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return URGENT_PHONE
    user_data['email'] = text
    await update.message.reply_text('Введите ИНН вашей организации (необязательно):', reply_markup=ReplyKeyboardMarkup(skip_keyboard, one_time_keyboard=True))
    return URGENT_INN

async def urgent_inn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите ваш email:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return URGENT_EMAIL
    if text == 'Пропустить':
        user_data['inn'] = 'Не указан'
    else:
        if validate_inn(text):
            user_data['inn'] = text
        else:
            await update.message.reply_text('ИНН должен содержать 10 или 12 цифр. Введите корректный ИНН или нажмите "Пропустить":', reply_markup=ReplyKeyboardMarkup(skip_keyboard, one_time_keyboard=True))
            return URGENT_INN
    # Формируем заявку
    username = update.message.from_user.username or "Не указан"
    first_name = update.message.from_user.first_name or "Не указано"
    request_text = (
        f"🚨 СРОЧНАЯ ПОДМЕНА\n"
        f"👤 Пользователь: @{username} ({first_name})\n"
        f"📋 Оборудование: {user_data['equipment_type'].upper()}, {user_data.get('equipment_model', 'Не указано')}\n"
        f"📝 Проблема: {user_data.get('problem_description', 'Не указано')}\n"
        f"📞 Телефон: {user_data.get('phone', 'Не указан')}\n"
        f"📧 Email: {user_data.get('email', 'Не указан')}\n"
        f"🔢 ИНН: {user_data.get('inn', 'Не указан')}\n"
        f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await context.bot.send_message(chat_id=CHANNEL_URGENT, text=request_text)
    await update.message.reply_text(
        '✅ <b>Заявка принята!</b>\n\n📞 Консультант свяжется с вами в течение 15 минут для подбора модели и расчета персональных условий.\n\nДля новой заявки отправьте /start',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ===== РЕМОНТ =====
async def repair_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_data['service_type'] = 'repair'
    await update.message.reply_text(
        '🔧 <b>РЕМОНТ ОБОРУДОВАНИЯ</b>\n\n'
        'Мы поможем с ремонтом любого медицинского оборудования:\n'
        '• КТ, МРТ, Рентген\n• УЗИ, ИВЛ, Эндоскопия\n• НДА и другое оборудование\n\n'
        'Выберите тип оборудования:',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(repair_type_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return REPAIR_TYPE

async def repair_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Выберите услугу:', reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return MAIN_MENU
    user_data['equipment_type'] = text
    await update.message.reply_text('Введите модель аппарата:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return REPAIR_MODEL

async def repair_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Выберите тип оборудования:', reply_markup=ReplyKeyboardMarkup(repair_type_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return REPAIR_TYPE
    user_data['equipment_model'] = text
    await update.message.reply_text('Опишите проблему с оборудованием:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return REPAIR_PROBLEM

async def repair_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите модель аппарата:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return REPAIR_MODEL
    user_data['problem_description'] = text
    await update.message.reply_text('Введите ваш телефон для связи:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return REPAIR_PHONE

async def repair_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Опишите проблему с оборудованием:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return REPAIR_PROBLEM
    user_data['phone'] = text
    await update.message.reply_text('Введите ваш email:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return REPAIR_EMAIL

async def repair_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите ваш телефон для связи:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return REPAIR_PHONE
    user_data['email'] = text
    await update.message.reply_text('Введите ИНН вашей организации (необязательно):', reply_markup=ReplyKeyboardMarkup(skip_keyboard, one_time_keyboard=True))
    return REPAIR_INN

async def repair_inn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите ваш email:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return REPAIR_EMAIL
    if text == 'Пропустить':
        user_data['inn'] = 'Не указан'
    else:
        if validate_inn(text):
            user_data['inn'] = text
        else:
            await update.message.reply_text('ИНН должен содержать 10 или 12 цифр. Введите корректный ИНН или нажмите "Пропустить":', reply_markup=ReplyKeyboardMarkup(skip_keyboard, one_time_keyboard=True))
            return REPAIR_INN
    # Формируем заявку
    username = update.message.from_user.username or "Не указан"
    first_name = update.message.from_user.first_name or "Не указано"
    request_text = (
        f"🔧 ЗАЯВКА НА РЕМОНТ\n"
        f"👤 Пользователь: @{username} ({first_name})\n"
        f"📋 Оборудование: {user_data['equipment_type']}, {user_data.get('equipment_model', 'Не указано')}\n"
        f"📝 Проблема: {user_data.get('problem_description', 'Не указано')}\n"
        f"📞 Телефон: {user_data.get('phone', 'Не указан')}\n"
        f"📧 Email: {user_data.get('email', 'Не указан')}\n"
        f"🔢 ИНН: {user_data.get('inn', 'Не указан')}\n"
        f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await context.bot.send_message(chat_id=CHANNEL_REPAIR, text=request_text)
    await update.message.reply_text(
        '✅ <b>Заявка принята!</b>\n\n📞 Консультант свяжется с вами в течение 15 минут для уточнения деталей.\n\nДля новой заявки отправьте /start',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ===== АРЕНДА =====
async def rental_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_data['service_type'] = 'rental'
    await update.message.reply_text(
        '🧪 <b>АРЕНДА ОБОРУДОВАНИЯ</b>\n\n'
        'Аренда оборудования для:\n• Тестирования нового направления\n• Для лицензии\n• Временной подмены\n\n'
        'Выберите цель аренды:',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(rental_purpose_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return RENTAL_PURPOSE

async def rental_purpose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Выберите услугу:', reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return MAIN_MENU
    user_data['purpose'] = text
    await update.message.reply_text('Введите тип оборудования:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return RENTAL_TYPE

async def rental_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Выберите цель аренды:', reply_markup=ReplyKeyboardMarkup(rental_purpose_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return RENTAL_PURPOSE
    user_data['equipment_type'] = text
    await update.message.reply_text('Введите модель аппарата:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return RENTAL_MODEL

async def rental_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите тип оборудования:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return RENTAL_TYPE
    user_data['equipment_model'] = text
    await update.message.reply_text('Введите ваш телефон для связи:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return RENTAL_PHONE

async def rental_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите модель аппарата:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return RENTAL_MODEL
    user_data['phone'] = text
    await update.message.reply_text('Введите ваш email:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return RENTAL_EMAIL

async def rental_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите ваш телефон для связи:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return RENTAL_PHONE
    user_data['email'] = text
    await update.message.reply_text('Введите ИНН вашей организации (необязательно):', reply_markup=ReplyKeyboardMarkup(skip_keyboard, one_time_keyboard=True))
    return RENTAL_INN

async def rental_inn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите ваш email:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return RENTAL_EMAIL
    if text == 'Пропустить':
        user_data['inn'] = 'Не указан'
    else:
        if validate_inn(text):
            user_data['inn'] = text
        else:
            await update.message.reply_text('ИНН должен содержать 10 или 12 цифр. Введите корректный ИНН или нажмите "Пропустить":', reply_markup=ReplyKeyboardMarkup(skip_keyboard, one_time_keyboard=True))
            return RENTAL_INN
    # Формируем заявку
    username = update.message.from_user.username or "Не указан"
    first_name = update.message.from_user.first_name or "Не указано"
    request_text = (
        f"🧪 ЗАЯВКА НА АРЕНДУ\n"
        f"👤 Пользователь: @{username} ({first_name})\n"
        f"🎯 Цель: {user_data['purpose']}\n"
        f"📋 Оборудование: {user_data['equipment_type']}, {user_data.get('equipment_model', 'Не указано')}\n"
        f"📞 Телефон: {user_data.get('phone', 'Не указан')}\n"
        f"📧 Email: {user_data.get('email', 'Не указан')}\n"
        f"🔢 ИНН: {user_data.get('inn', 'Не указан')}\n"
        f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await context.bot.send_message(chat_id=CHANNEL_RENTAL, text=request_text)
    await update.message.reply_text(
        '✅ <b>Заявка принята!</b>\n\n📞 Консультант свяжется с вами в течение 15 минут для подбора оборудования.\n\nДля новой заявки отправьте /start',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ===== АУДИТ =====
async def audit_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_data['service_type'] = 'audit'
    await update.message.reply_text(
        '📊 <b>БЕСПЛАТНЫЙ АУДИТ ОБОРУДОВАНИЯ</b>\n\n'
        'Мы проведем анализ:\n• Рисков простоя оборудования\n• Планов по замене\n• Оптимизации парка\n\n'
        'Введите ваш телефон для связи:',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True)
    )
    return AUDIT_PHONE

async def audit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Выберите услугу:', reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return MAIN_MENU
    user_data['phone'] = text
    await update.message.reply_text('Введите ваш email:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
    return AUDIT_EMAIL

async def audit_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите ваш телефон для связи:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return AUDIT_PHONE
    user_data['email'] = text
    await update.message.reply_text('Введите ИНН вашей организации (необязательно):', reply_markup=ReplyKeyboardMarkup(skip_keyboard, one_time_keyboard=True))
    return AUDIT_INN

async def audit_inn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    text = update.message.text
    if text == 'Назад':
        await update.message.reply_text('Введите ваш email:', reply_markup=ReplyKeyboardMarkup(back_only_keyboard, one_time_keyboard=True))
        return AUDIT_EMAIL
    if text == 'Пропустить':
        user_data['inn'] = 'Не указан'
    else:
        if validate_inn(text):
            user_data['inn'] = text
        else:
            await update.message.reply_text('ИНН должен содержать 10 или 12 цифр. Введите корректный ИНН или нажмите "Пропустить":', reply_markup=ReplyKeyboardMarkup(skip_keyboard, one_time_keyboard=True))
            return AUDIT_INN
    # Формируем заявку
    username = update.message.from_user.username or "Не указан"
    first_name = update.message.from_user.first_name or "Не указано"
    request_text = (
        f"📊 ЗАЯВКА НА АУДИТ\n"
        f"👤 Пользователь: @{username} ({first_name})\n"
        f"📞 Телефон: {user_data.get('phone', 'Не указан')}\n"
        f"📧 Email: {user_data.get('email', 'Не указан')}\n"
        f"🔢 ИНН: {user_data.get('inn', 'Не указан')}\n"
        f"🕒 Время: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await context.bot.send_message(chat_id=CHANNEL_AUDIT, text=request_text)
    await update.message.reply_text(
        '✅ <b>Заявка принята!</b>\n\n📞 Консультант свяжется с вами в течение 15 минут для проведения аудита.\n\nДля новой заявки отправьте /start',
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ===== ОБРАБОТКА ГЛАВНОГО МЕНЮ =====
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == '⚡️ СРОЧНАЯ ПОДМЕНА ОБОРУДОВАНИЯ':
        return await urgent_replace(update, context)
    elif text == '🔧 РЕМОНТ':
        return await repair_service(update, context)
    elif text == '🧪 АРЕНДА ОБОРУДОВАНИЯ':
        return await rental_service(update, context)
    elif text == '📊 БЕСПЛАТНЫЙ АУДИТ ОБОРУДОВАНИЯ':
        return await audit_service(update, context)
    else:
        await update.message.reply_text('Пожалуйста, выберите вариант из меню:', reply_markup=ReplyKeyboardMarkup(main_menu_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Диалог прерван. Для начала отправьте /start', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def main_async():
    """Асинхронная версия основной функции"""
    TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    application = Application.builder().token(TOKEN).build()

    # Обработчики для каждого типа услуг
    urgent_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text('⚡️ СРОЧНАЯ ПОДМЕНА ОБОРУДОВАНИЯ'), urgent_replace)],
        states={
            URGENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, urgent_type)],
            URGENT_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, urgent_model)],
            URGENT_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, urgent_problem)],
            URGENT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, urgent_phone)],
            URGENT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, urgent_email)],
            URGENT_INN: [MessageHandler(filters.TEXT & ~filters.COMMAND, urgent_inn)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    repair_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text('🔧 РЕМОНТ'), repair_service)],
        states={
            REPAIR_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, repair_type)],
            REPAIR_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, repair_model)],
            REPAIR_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, repair_problem)],
            REPAIR_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, repair_phone)],
            REPAIR_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, repair_email)],
            REPAIR_INN: [MessageHandler(filters.TEXT & ~filters.COMMAND, repair_inn)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    rental_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text('🧪 АРЕНДА ОБОРУДОВАНИЯ'), rental_service)],
        states={
            RENTAL_PURPOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, rental_purpose)],
            RENTAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, rental_type)],
            RENTAL_MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, rental_model)],
            RENTAL_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, rental_phone)],
            RENTAL_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, rental_email)],
            RENTAL_INN: [MessageHandler(filters.TEXT & ~filters.COMMAND, rental_inn)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    audit_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Text('📊 БЕСПЛАТНЫЙ АУДИТ ОБОРУДОВАНИЯ'), audit_service)],
        states={
            AUDIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, audit_phone)],
            AUDIT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, audit_email)],
            AUDIT_INN: [MessageHandler(filters.TEXT & ~filters.COMMAND, audit_inn)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Главный обработчик
    main_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(urgent_conv)
    application.add_handler(repair_conv)
    application.add_handler(rental_conv)
    application.add_handler(audit_conv)
    application.add_handler(main_conv)
    
    await application.run_polling()

def main():
    """Синхронная обертка для обратной совместимости"""
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
