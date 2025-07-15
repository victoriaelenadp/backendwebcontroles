from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrapear_paises_tabla_principal():
    options = Options()
    # options.headless = True  # Puedes activar esto si no quieres abrir ventana
    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://www.sanctionsmap.eu/#/main")

    try:
        wait = WebDriverWait(driver, 30)

        # Espera hasta que los spans con países estén presentes
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a")))

        spans = driver.find_elements(By.CSS_SELECTOR, "a")

        # Filtra solo los spans que tienen nombre de país (algunos están vacíos o son duplicados)
        paises = [span.text.strip() for span in spans if span.text.strip()]

    except Exception as e:
        print("❌ Error al scrapear:", e)
        paises = []
    finally:
        driver.quit()

    return sorted(set(paises))  # Quita duplicados y ordena

if __name__ == "__main__":
    paises = scrapear_paises_tabla_principal()
    print("🌍 Paises sancionados encontrados:")
    for pais in paises:
        print("-", pais)
