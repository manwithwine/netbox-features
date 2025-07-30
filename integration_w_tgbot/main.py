import logging
import os
import pynetbox

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get configuration from environment variables
NETBOX_URL = os.getenv('NETBOX_URL')
NETBOX_TOKEN = os.getenv('NETBOX_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Initialize NetBox API
netbox = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# States for conversation
TAKE, RETURN, SCAN_BARCODE, SET_QUANTITY, SELECT_CATEGORY, REGISTER, MAIN_MENU, SET_MULTI_QUANTITY = range(8)

# File to store users and logs
USERS_FILE = "users.txt"
LOGS_FILE = "logs.txt"


def load_users():
    """Load users from file with proper formatting."""
    users = {}
    if not os.path.exists(USERS_FILE):
        return users

    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and '- ФИО:' in line:  # Only process properly formatted lines
                user_id, name = line.split(' - ФИО: ', 1)
                try:
                    users[int(user_id)] = name.strip()
                except ValueError:
                    continue
    return users


def save_user(user_id, full_name):
    """Save a new user to the file with proper formatting and newlines."""
    # First load existing users to prevent duplicates
    existing_users = load_users()

    # Add/update the user
    existing_users[user_id] = full_name

    # Write all users back to file with proper formatting
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        for uid, name in existing_users.items():
            f.write(f"{uid} - ФИО: {name}\n")  # Ensures newline after each entry


async def register_user(update: Update, context: CallbackContext) -> int:
    """Handle user registration with improved validation."""
    user_id = update.effective_user.id
    full_name = update.message.text.strip()

    # Enhanced validation
    name_parts = full_name.split()
    if len(name_parts) < 2:
        await update.message.reply_text(
            "❌ Укажите, пожалуйста ваши Фамилию и Имя:\n"
            "Пример: Иванов Иван"
        )
        return REGISTER

    # Check for existing registration
    users = load_users()
    if user_id in users:
        await update.message.reply_text(
            f"ℹ️ Вы уже зарегистрированы как: {users[user_id]}\n"
            "Выберите действие:",
            reply_markup=main_keyboard
        )
        return TAKE

    # Save the user with proper formatting
    save_user(user_id, full_name)
    context.user_data['full_name'] = full_name

    await update.message.reply_text(
        f"✅ Регистрация выполнена!\n"
        f"ФИО: {full_name}\n\n"
        "Выберите действие:",
        reply_markup=main_keyboard
    )
    return TAKE


async def start(update: Update, context: CallbackContext) -> int:
    """Check if user is registered or start registration."""
    user_id = update.effective_user.id
    users = load_users()

    if user_id in users:
        context.user_data['full_name'] = users[user_id]
        await update.message.reply_text(
            f"Добро пожаловать, {users[user_id]}! Выберите действие:",
            reply_markup=main_keyboard
        )
        return TAKE
    else:
        await update.message.reply_text(
            "👋 Приветствую! Укажите, пожалуйста, ваши Фамилию и Имя:\n"
            "Пример: Иванов Иван"
        )
        return REGISTER

# Add category keyboard
category_keyboard = [['DAC', 'AOC'], ['SFP', 'SAS'], ['Other']]
category_markup = ReplyKeyboardMarkup(category_keyboard, one_time_keyboard=True)

# Keyboard
main_keyboard = ReplyKeyboardMarkup(
    [['Взять', 'Вернуть'], ['Посмотреть']],
    one_time_keyboard=True,
    resize_keyboard=True
)

back_keyboard = ReplyKeyboardMarkup(
    [['Назад']],
    one_time_keyboard=True,
    resize_keyboard=True
)

category_keyboard = ReplyKeyboardMarkup(
    [['DAC', 'AOC'], ['SFP', 'SAS'], ['Other', 'Назад']],
    one_time_keyboard=True,
    resize_keyboard=True
)

async def stop(update: Update, context: CallbackContext) -> int:
    """Clear user session and return to start"""
    context.user_data.clear()
    await update.message.reply_text(
        "🛑 Ваша сессия сброшена. Для старта нажмите на /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def handle_take_return(update: Update, context: CallbackContext) -> int:
    """Handles user selection of Take, Return, or Show Items."""
    user_choice = update.message.text
    if user_choice == 'Назад':
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_keyboard
        )
        return TAKE
    elif user_choice in ['Взять', 'Вернуть']:
        context.user_data['action'] = user_choice
        await update.message.reply_text(
            f"Просьба сканировать штрихкод расходника, который Вы хотите {user_choice.lower()}.",
            reply_markup=back_keyboard
        )
        return SCAN_BARCODE
    elif user_choice == 'Посмотреть':
        await update.message.reply_text(
            "Какой тип расходника Вас интересует?",
            reply_markup=category_keyboard
        )
        return SELECT_CATEGORY
    else:
        await update.message.reply_text("⚠️ Неизвестная команда", reply_markup=main_keyboard)
        return TAKE


async def handle_barcode(update: Update, context: CallbackContext) -> int:
    """Handles barcode input and routes to appropriate handler."""
    if update.message.text == 'Назад':
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_keyboard
        )
        return TAKE

    barcodes = [b.strip() for b in update.message.text.split('\n') if b.strip()]

    if len(barcodes) == 1:
        # Single barcode - show item info before asking for quantity
        barcode = barcodes[0]
        items = netbox.dcim.inventory_items.filter(custom_fields={'Barcode': barcode})
        valid_items = [item for item in items if item.custom_fields.get('Barcode') == barcode]

        if not valid_items:
            await update.message.reply_text(
                f"❌ Расходник с штрихкодом {barcode} не найден",
                reply_markup=back_keyboard
            )
            return SCAN_BARCODE
        elif len(valid_items) > 1:
            await update.message.reply_text(
                f"❌ Найдено несколько расходников с штрихкодом {barcode}",
                reply_markup=back_keyboard
            )
            return SCAN_BARCODE

        # Store item info and show to user
        item = valid_items[0]
        context.user_data['item_info'] = {
            'item': item,
            'barcode': barcode
        }

        await update.message.reply_text(
            f"🔍 Найден расходник:\n"
            f"```\n"
            f"Название: {item.name}\n"
            f"Текущее количество: {item.custom_fields.get('Quantity', 0)}\n"
            f"```\n"
            "Просьба указать кол-во:",
            parse_mode='Markdown',
            reply_markup=back_keyboard
        )
        return SET_QUANTITY
    else:
        # Multiple barcodes - use multi-item flow
        items_info = []
        invalid_barcodes = []

        for barcode in barcodes:
            items = netbox.dcim.inventory_items.filter(custom_fields={'Barcode': barcode})
            valid_items = [item for item in items if item.custom_fields.get('Barcode') == barcode]

            if not valid_items:
                invalid_barcodes.append(barcode)
            elif len(valid_items) > 1:
                invalid_barcodes.append(f"{barcode} (multiple matches)")
            else:
                items_info.append({
                    'item': valid_items[0],
                    'barcode': barcode,
                    'quantity': valid_items[0].custom_fields.get('Quantity', 0)
                })

        # Store items info for later processing
        context.user_data['multi_items'] = items_info
        context.user_data['invalid_barcodes'] = invalid_barcodes

        # Prepare items list for user
        items_list = []
        for idx, item_info in enumerate(items_info, start=1):
            items_list.append(
                f"{idx}. {item_info['item'].name} (штрихкод: {item_info['barcode']}) - Кол-во: {item_info['quantity']}"
            )

        message = (
            f"🔍 Найдены расходники:\n"
            f"```\n"
            f"{'\n'.join(items_list)}\n"
            f"```\n\n"
            f"Сколько Вы планируете {context.user_data['action'].lower()}?\n"
            f"Укажите кол-во для каждого расходника в том же порядке (по одному числу в строке):"
        )

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=back_keyboard
        )
        return SET_MULTI_QUANTITY


async def handle_multi_quantity(update: Update, context: CallbackContext) -> int:
    """Handles quantity input for multiple items."""
    if update.message.text == 'Назад':
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_keyboard
        )
        return TAKE

    try:
        quantities = [int(q.strip()) for q in update.message.text.split('\n') if q.strip()]
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите только числа (по одному на строку)",
            reply_markup=main_keyboard
        )
        return SET_MULTI_QUANTITY

    items_info = context.user_data.get('multi_items', [])
    invalid_barcodes = context.user_data.get('invalid_barcodes', [])
    action = context.user_data['action']
    user = context.user_data.get('full_name', update.effective_user.full_name)

    if len(quantities) != len(items_info):
        await update.message.reply_text(
            f"❌ Количество чисел ({len(quantities)}) не совпадает с количеством расходников ({len(items_info)})",
            reply_markup=main_keyboard
        )
        return SET_MULTI_QUANTITY

    results = []
    for idx, (item_info, quantity) in enumerate(zip(items_info, quantities), start=1):
        item = item_info['item']
        barcode = item_info['barcode']
        current_quantity = item.custom_fields.get('Quantity', 0)
        item_name = item.name

        try:
            if action == "Взять":
                if current_quantity < quantity:
                    results.append(f"{idx}. ❌ Недостаточно {item_name} (есть {current_quantity}, нужно {quantity})")
                    continue

                item.custom_fields['Quantity'] = current_quantity - quantity
                item.description = f"Взят сотрудником {user}"
                item.save()
                log_transaction(action, user, item_name, barcode, quantity)
                results.append(f"{idx}. ✅ Взято {quantity} {item_name}")

            elif action == "Вернуть":
                item.custom_fields['Quantity'] = current_quantity + quantity
                item.description = f"Возвращен сотрудником: {user}"
                item.save()
                log_transaction(action, user, item_name, barcode, quantity)
                results.append(f"{idx}. ✅ Возвращено {quantity} {item_name}")
        except Exception as e:
            logger.error(f"Error processing item {item_name}: {e}")
            results.append(f"{idx}. ❌ Ошибка обработки {item_name}")

    # Prepare result message
    message = "Результаты:\n" + "\n".join(results)
    if invalid_barcodes:
        message += f"\n\n⚠ Необработанные штрихкоды: {', '.join(invalid_barcodes)}"

    await update.message.reply_text(
        message,
        reply_markup=main_keyboard
    )
    return TAKE


async def handle_category_selection(update: Update, context: CallbackContext) -> int:
    """Handles category selection and shows filtered items."""
    if update.message.text == 'Назад':
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_keyboard
        )
        return TAKE
    category = update.message.text
    context.user_data['category'] = category

    try:
        # Fetch all inventory items
        items = list(netbox.dcim.inventory_items.all())
    except Exception as e:
        logger.error(f"Ошибка Netbox: {e}, просьба обратиться на ur_mail_server")
        await update.message.reply_text("❌ Пу пу пупу", reply_markup=main_keyboard)
        return TAKE

    # Filter items based on category
    filtered_items = []
    for item in items:
        name = item.name.upper()
        if category == 'DAC' and name.startswith('DAC'):
            filtered_items.append(item)
        elif category == 'AOC' and name.startswith('AOC'):
            filtered_items.append(item)
        elif category == 'SAS' and name.startswith('SAS'):
            filtered_items.append(item)
        elif category == 'SFP' and (name.startswith('SFP') or name.startswith('OTHER SFP')):
            filtered_items.append(item)
        elif category == 'Other':
            if not (name.startswith('DAC') or
                   name.startswith('AOC') or
                   name.startswith('SFP') or
                   name.startswith('OTHER SFP') or
                   name.startswith('SAS')):
                filtered_items.append(item)
    # Special handling for "Other" category - show all items individually
    if category == 'Other':
        # Prepare message chunks
        message_chunks = []
        current_chunk = []

        # Add header outside code block
        header = f"📦 {category}:"
        current_chunk.append(header)
        current_chunk.append("```")

        # Add column headers
        col_header = "• Имя                       Ящик              Кол-во"
        current_chunk.append(col_header)
        current_chunk.append("-" * 60)  # Separator line

        # Add all items individually
        for item in sorted(filtered_items, key=lambda x: x.name):
            quantity = item.custom_fields.get('Quantity', 0)
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                quantity = 0

            device_name = getattr(item.device, 'name', 'N/A') if item.device else 'N/A'
            line = f"• {item.name.ljust(25)} {device_name.ljust(20)} {quantity}"

            if len('\n'.join(current_chunk) + '\n' + line) + len("```") > 4000:
                current_chunk.append("```")
                message_chunks.append('\n'.join(current_chunk))
                current_chunk = [header, "```", col_header, "-" * 60]

            current_chunk.append(line)

        # Close the final code block if there's content
        if len(current_chunk) > 2:
            current_chunk.append("```")
            message_chunks.append('\n'.join(current_chunk))

        # Send all chunks
        if not message_chunks:
            await update.message.reply_text(
                f"ℹ️ В категории '{category}' расходников не найдено",
                reply_markup=main_keyboard
            )
        else:
            for i, chunk in enumerate(message_chunks):
                try:
                    await update.message.reply_text(
                        chunk,
                        reply_markup=main_keyboard if i == len(message_chunks) - 1 else None,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Error sending message chunk: {e}")
                    await update.message.reply_text(
                        "⚠️ Ошибка при отображении списка расходников",
                        reply_markup=main_keyboard
                    )

        return TAKE

    # Try different ways to get Part ID
    def get_part_id(item):
        # Try direct custom field access with different naming conventions
        for field_name in ['Part ID', 'part_id', 'Part_ID', 'part-id', 'part id']:
            if field_name in item.custom_fields:
                part_id = item.custom_fields[field_name]
                if part_id and str(part_id).strip().lower() not in ['none', 'n/a', '']:
                    return str(part_id).strip()

        # Try to get from the part_id attribute directly
        if hasattr(item, 'part_id'):
            part_id = getattr(item, 'part_id')
            if part_id and str(part_id).strip().lower() not in ['none', 'n/a', '']:
                return str(part_id).strip()

        # Try to get from the role field (sometimes used as part ID)
        if hasattr(item, 'role'):
            role = getattr(item, 'role')
            if role and str(role).strip().lower() not in ['none', 'n/a', '']:
                return str(role).strip()

        return None

    # Separate items into those with and without part IDs
    items_with_part_id = []
    items_without_part_id = []

    for item in filtered_items:
        part_id = get_part_id(item)
        if part_id:
            items_with_part_id.append((item, part_id))
        else:
            items_without_part_id.append(item)

    # Group items with part IDs by base name and part ID
    inventory_summary = {}
    for item, part_id in items_with_part_id:
        # Extract base part name
        name_parts = item.name.split('-')
        base_name = '-'.join(name_parts[:-1]) if len(name_parts) > 1 else item.name

        # Get device name if available
        device_name = getattr(item.device, 'name', 'N/A') if item.device else 'N/A'

        quantity = item.custom_fields.get('Quantity', 0)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 0

        summary_key = f"{base_name}|{part_id}|{device_name}"

        if summary_key in inventory_summary:
            inventory_summary[summary_key]['quantity'] += quantity
        else:
            inventory_summary[summary_key] = {
                'base_name': base_name,
                'part_id': part_id,
                'device': device_name,  # Add device information
                'quantity': quantity
            }

    # Calculate column widths
    max_name_len = max(len(data['base_name']) for data in inventory_summary.values()) if inventory_summary else 0
    max_part_id_len = max(len(data['part_id']) for data in inventory_summary.values()) if inventory_summary else 0
    max_device_len = max(len(data['device']) for data in inventory_summary.values()) if inventory_summary else 0

    # Set minimum column widths
    max_name_len = max(max_name_len, 15)  # Minimum width for name column
    max_part_id_len = max(max_part_id_len, 15)  # Minimum width for part ID column
    max_device_len = max(max_device_len, 10)


    # Prepare the formatted output
    message_chunks = []
    current_chunk = []

    # Add header outside code block
    header = f"📦 {category}:"
    current_chunk.append(header)
    current_chunk.append("```")

    # Add column headers with device
    col_header = (f"• {'Имя'.ljust(max_name_len)}  {'P/N'.ljust(max_part_id_len)}  "
                  f"{'Ящик'.ljust(max_device_len)}  Кол-во")
    current_chunk.append(col_header)
    separator = "-" * (max_name_len + max_part_id_len + max_device_len + 15)
    current_chunk.append(separator)

    # Add summarized items with device info
    if inventory_summary:
        for key, data in sorted(inventory_summary.items(), key=lambda x: x[1]['base_name']):
            line = (f"• {data['base_name'].ljust(max_name_len)}  "
                    f"{data['part_id'].ljust(max_part_id_len)}  "
                    f"{data['device'].ljust(max_device_len)}  "
                    f"{data['quantity']}")

            if len('\n'.join(current_chunk) + '\n' + line) + len("```") > 4000:
                current_chunk.append("```")
                message_chunks.append('\n'.join(current_chunk))
                current_chunk = [header, "```", col_header, separator]

            current_chunk.append(line)

    # Add individual items if they exist
    if items_without_part_id:
        if len(current_chunk) > 4:  # If we have content beyond header and col headers
            current_chunk.append("```")
            message_chunks.append('\n'.join(current_chunk))
            current_chunk = [header, "```"]

        current_chunk.append("Расходники без P/N:")
        for item in sorted(items_without_part_id, key=lambda x: x.name):
            quantity = item.custom_fields.get('Quantity', 0)
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                quantity = 0

            line = f"• {item.name}: Qty {quantity}"

            if len('\n'.join(current_chunk) + '\n' + line) + len("```") > 4000:
                current_chunk.append("```")
                message_chunks.append('\n'.join(current_chunk))
                current_chunk = [header, "```", "Расходники без P/N (cont.):"]

            current_chunk.append(line)

    # Close the final code block if there's content
    if len(current_chunk) > 2:  # More than just header and opening ```
        current_chunk.append("```")
        message_chunks.append('\n'.join(current_chunk))

    # Send all chunks
    if not message_chunks:
        await update.message.reply_text(
            f"ℹ️ No {category} items found",
            reply_markup=main_keyboard
        )
    else:
        for i, chunk in enumerate(message_chunks):
            try:
                await update.message.reply_text(
                    chunk,
                    reply_markup=main_keyboard if i == len(message_chunks) - 1 else None,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error sending message chunk: {e}")
                await update.message.reply_text(
                    "⚠️ Error displaying some inventory items",
                    reply_markup=main_keyboard
                )
    return TAKE


async def handle_quantity(update: Update, context: CallbackContext) -> int:
    """Handles quantity input for a single item."""
    if update.message.text == 'Назад':
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_keyboard
        )
        return TAKE
    try:
        quantity = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите только число",
            reply_markup=main_keyboard
        )
        return SET_QUANTITY

    action = context.user_data['action']
    item_info = context.user_data.get('item_info')
    if not item_info:
        await update.message.reply_text(
            "❌ Ошибка: информация о расходнике не найдена",
            reply_markup=main_keyboard
        )
        return TAKE

    item = item_info['item']
    barcode = item_info['barcode']
    user = context.user_data.get('full_name', update.effective_user.full_name)
    item_name = item.name
    current_quantity = item.custom_fields.get('Quantity', 0)

    try:
        if action == "Взять":
            if current_quantity <= 0:
                await update.message.reply_text(
                    f"❌ {item_name} уже взят (количество 0)",
                    reply_markup=main_keyboard
                )
                return TAKE

            if quantity > current_quantity:
                await update.message.reply_text(
                    f"❌ Недостаточно {item_name} (есть {current_quantity}, нужно {quantity})",
                    reply_markup=main_keyboard
                )
                return TAKE

            item.custom_fields['Quantity'] = current_quantity - quantity
            item.description = f"Взят сотрудником {user}"
            item.status = "active"
            item.save()

            # Log the transaction
            log_transaction(action, user, item_name, barcode, quantity)

            await update.message.reply_text(
                f"✅ Успешно взято {quantity} {item_name}\n"
                f"Оставшееся кол-во: {item.custom_fields['Quantity']}",
                reply_markup=main_keyboard
            )

        elif action == "Вернуть":
            item.custom_fields['Quantity'] = current_quantity + quantity
            item.description = f"Возвращен сотрудником: {user}"
            item.status = "offline"
            item.save()

            # Log the transaction
            log_transaction(action, user, item_name, barcode, quantity)

            await update.message.reply_text(
                f"✅ Успешно возвращено {quantity} {item_name}\n"
                f"Новое кол-во: {item.custom_fields['Quantity']}",
                reply_markup=main_keyboard
            )
    except Exception as e:
        logger.error(f"Error processing item {item_name}: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при обработке {item_name}",
            reply_markup=main_keyboard
        )

    return TAKE


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels the operation and restarts."""
    await update.message.reply_text("Operation cancelled. Restarting.")
    return TAKE  # Restart instead of ending


def log_transaction(action: str, full_name: str, item_name: str, barcode: str, quantity: int):
    """Log transaction to file with timestamp."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    log_entry = (
        f"{timestamp}, "
        f"ФИО: {full_name}, "
        f"{'Взял' if action == 'Take' else 'Вернул'}, "
        f"Имя: {item_name}, "
        f"Штрихкод: {barcode}, "
        f"Qty: {quantity}\n"
    )

    with open(LOGS_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def main() -> None:
    """Main function with logging setup."""
    if not os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            f.write("Transactions Log:\n")
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REGISTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_user)],
            TAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_take_return)],
            SELECT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_selection)],
            SCAN_BARCODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_barcode)],
            SET_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity)],
            SET_MULTI_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_multi_quantity)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('stop', stop)
        ],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    # Create users file if it doesn't exist
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE, 'a').close()

    main()