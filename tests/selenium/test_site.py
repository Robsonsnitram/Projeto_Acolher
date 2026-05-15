from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

options = Options()

options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

try:

    print("Abrindo site...")

    driver.get("https://espacoacolher.site")

    time.sleep(3)

    titulo = driver.title

    print("Título encontrado:")
    print(titulo)

    assert "Acolher" in titulo

    print("Teste executado com sucesso!")

finally:

    driver.quit()