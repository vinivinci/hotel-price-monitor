import os
import time
import re
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from twilio.rest import Client

load_dotenv()

def get_page_source(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/114.0.0.0 Safari/537.36")

    
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    
    time.sleep(10)
    html = driver.page_source
    driver.quit()
    return html

def extract_hotel_price(html, hotel_name):
    soup = BeautifulSoup(html, 'html.parser')
    
    articles = soup.find_all('article', attrs={'itemtype': 'https://schema.org/Hotel'})
    
    for article in articles:
        name_tag = article.find(attrs={'itemprop': 'name'})
        if name_tag:
            hotel_name_text = name_tag.get_text(strip=True)
            if hotel_name.lower() in hotel_name_text.lower():
                price_tag = article.find('span', attrs={'data-testid': 'recommended-price', 'itemprop': 'price'})
                if price_tag:
                    price_text = price_tag.get_text(strip=True)
                    cleaned_price = re.sub(r'[^\d,\.]', '', price_text)
                    if '.' in cleaned_price and ',' not in cleaned_price:
                        cleaned_price = cleaned_price.replace('.', '')

                    elif ',' in cleaned_price:
                        cleaned_price = cleaned_price.replace(',', '.')
                    try:
                        return float(cleaned_price)
                    except Exception as e:
                        print("Erro convertendo o preço:", e)
                        return None
    return None

def send_whatsapp_notification(message_text):
    account_sid = os.environ.get("TWILIO_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    whatsapp_from = os.environ.get("TWILIO_WHATSAPP_FROM")
    whatsapp_to = os.environ.get("TWILIO_WHATSAPP_TO")
    
    client = Client(account_sid, auth_token)
    msg = client.messages.create(
        body=message_text,
        from_="whatsapp:" + whatsapp_from,
        to="whatsapp:" + whatsapp_to
    )
    print("Mensagem WhatsApp enviada. SID:", msg.sid)

def main():
    trivago_url = os.environ.get("TRIVAGO_URL")
    hotel_name = os.environ.get("HOTEL_NAME")
    price_threshold_str = os.environ.get("PRICE_THRESHOLD", "0")
    
    try:
        price_threshold = float(price_threshold_str)
    except ValueError:
        print("PRICE_THRESHOLD inválido. Use um valor numérico.")
        return

    if not trivago_url or not hotel_name:
        print("As variáveis TRIVAGO_URL e HOTEL_NAME devem estar definidas no .env.")
        return

    print("Acessando a URL do Trivago...")
    html = get_page_source(trivago_url)

    print("Extraindo o preço para o hotel:", hotel_name)
    price = extract_hotel_price(html, hotel_name)
    if price is None:
        print("Não foi possível localizar o hotel ou extrair o preço.")
        return

    print(f"Preço encontrado para '{hotel_name}': R$ {price:.2f}")
    if price < price_threshold:
        message = (f"Alerta: O preço do {hotel_name} está abaixo do limite estipulado!\n"
                   f"Preço atual: R$ {price:.2f} (Limite: R$ {price_threshold:.2f})")
        print("Enviando notificação via WhatsApp...")
        send_whatsapp_notification(message)
    else:
        print("Preço acima do limite. Nenhuma notificação enviada.")

if __name__ == "__main__":
    main()
