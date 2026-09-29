from playwright.sync_api import sync_playwright
import time
import random
import string

# Configuration
URL = "https://x.com/i/premium_sign_up"
CLICK_1 = "#layers > div:nth-child(2) > div > div > div > div > div > div.css-175oi2r.r-1ny4l3l.r-18u37iz.r-1pi2tsx.r-1777fci.r-1xcajam.r-ipm5af.r-g6jmlv.r-1awozwy > div.css-175oi2r.r-1wbh5a2.r-htvplk.r-1udh08x.r-17gur6a.r-1pi2tsx.r-13qz1uu > div > div.css-175oi2r.r-1awozwy.r-13awgt0.r-f8sm7e.r-11c0sde.r-wech8c.r-3pj75a.r-13qz1uu > div:nth-child(2) > div > div > button:nth-child(1)"
CLICK_2 = "#layers > div:nth-child(2) > div > div > div > div > div > div.css-175oi2r.r-1ny4l3l.r-18u37iz.r-1pi2tsx.r-1777fci.r-1xcajam.r-ipm5af.r-g6jmlv.r-1awozwy > div.css-175oi2r.r-1wbh5a2.r-htvplk.r-1udh08x.r-17gur6a.r-1pi2tsx.r-13qz1uu > div > div.css-175oi2r.r-7qzcwe.r-ndvcnb.r-7jjzhb.r-1aybqs4.r-1pthbko.r-1phboty.r-5kkj8d.r-1p0dtai.r-18u37iz.r-1777fci.r-h3f8nf.r-nsbfu8.r-1xcajam.r-13qz1uu > div:nth-child(2) > div:nth-child(1) > div > div > button"
EMAIL_SELECTOR = "#email"
PAYMENT_METHOD_BUTTON = "#payment-form > div > div > div > div.PaymentMethodForm > div.Accordion.PaymentMethodFormAccordion > div:nth-child(2) > div > div > div > div > div > div > div > div > div > div > div > div.flex-item.width-grow > div"
IBAN_SELECTOR = "#iban"
NAME_SELECTOR = "#billingName"
ADDRESS_SELECTOR = "#billingAddressLine1"
POSTAL_SELECTOR = "#billingPostalCode"
CITY_SELECTOR = "#billingLocality"
CONFIRM_SELECTOR = "#payment-form > div > div > div > div.PaymentForm-confirmPaymentContainer.mt5.flex-item.width-grow > div > div:nth-child(3) > div > button > div.SubmitButton-IconContainer"

def random_email():
    """Génère un email aléatoire"""
    return ''.join(random.choices(string.ascii_lowercase, k=8)) + "@example.com"

def load_accounts(filename):
    """Charge les comptes depuis le fichier accounts.txt"""
    accounts = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        username = parts[0]
                        auth_token = parts[1]
                        accounts.append({
                            'username': username,
                            'auth_token': auth_token
                        })
        return accounts
    except:
        return []

def process_account(account, index, total):
    """Traite un compte individuel"""
    username = account['username']
    auth_token = account['auth_token']
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=['--auto-open-devtools-for-tabs']
            )
            context = browser.new_context()
            
            context.add_cookies([{
                "name": "auth_token",
                "value": auth_token,
                "domain": "x.com",
                "path": "/",
                "httpOnly": True,
                "secure": True
            }])
            
            page = context.new_page()
            page.goto(URL)
            time.sleep(5)
            
            page.locator(CLICK_1).click()
            time.sleep(2)
            
            page.locator(CLICK_2).click()
            time.sleep(2)
            
            page.locator(EMAIL_SELECTOR).fill(random_email())
            time.sleep(1)
            
            page.locator(PAYMENT_METHOD_BUTTON).click()
            time.sleep(2)
            
            page.locator(IBAN_SELECTOR).fill("DE03770698360521293028")
            time.sleep(0.5)
            
            page.locator(NAME_SELECTOR).fill("Reinhold Schön")
            time.sleep(0.5)
            
            page.locator(ADDRESS_SELECTOR).fill("Emil-Nohl-Str. 75c")
            time.sleep(0.5)
            
            page.locator(POSTAL_SELECTOR).fill("42897")
            time.sleep(0.5)
            
            page.locator(CITY_SELECTOR).fill("Laardo")
            time.sleep(1)
            
            page.locator(CONFIRM_SELECTOR).click()
            time.sleep(2)
            page.locator(CONFIRM_SELECTOR).click()
            
            time.sleep(15)
            
            # Vérifier si on est de retour sur x.com
            current_url = page.url
            is_success = current_url.startswith("https://x.com") and "premium_sign_up" not in current_url
            
            browser.close()
            
            return is_success
            
    except Exception as e:
        return False

def main():
    """Fonction principale"""
    accounts = load_accounts('accounts.txt')
    
    if not accounts:
        return
    
    success_count = 0
    failed_count = 0
    
    for i, account in enumerate(accounts, 1):
        if process_account(account, i, len(accounts)):
            success_count += 1
        else:
            failed_count += 1
        
        if i < len(accounts):
            time.sleep(5)
    
    print(f"\n✅ Réussis: {success_count} | ❌ Échoués: {failed_count} | Total: {len(accounts)}")

if __name__ == "__main__":
    main()