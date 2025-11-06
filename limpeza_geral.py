import time
import os  # <-- 1. IMPORTADO
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- Configurações para o GitHub Actions ---
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("window-size=1920,1080")

driver = webdriver.Chrome(options=options)

# Esperas
wait = WebDriverWait(driver, 20)
wait_curto = WebDriverWait(driver, 3)

URL_ORDENS_SERVICO = "https://sofitview.com.br/#/client/serviceorders"

# --- Lendo usuário e senha dos Secrets ---
USERNAME = os.environ.get("SOFIT_USER")
PASSWORD = os.environ.get("SOFIT_PASS")

if not USERNAME or not PASSWORD:
    print("❌ Erro: Variáveis de ambiente SOFIT_USER ou SOFIT_PASS não definidas.")
    driver.quit()
    exit()

# --- 2. CRIA A PASTA PARA SALVAR AS PROVAS ---
os.makedirs("screenshots", exist_ok=True)
# ---------------------------------------------

driver.get("https://sofitview.com.br/#/login")

try:
    print("Tentando fazer login...")
    campo_usuario = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//input[@placeholder='Informe seu usuário']")))
    campo_usuario.send_keys(USERNAME) 

    campo_senha = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//input[@type='password']")))
    campo_senha.send_keys(PASSWORD) 

    botao_login = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(., 'Fazer login')]")))
    botao_login.click()
    print("✅ Login feito com sucesso!")

    # --- 3. TIRA SCREENSHOT DO SUCESSO DO LOGIN ---
    driver.save_screenshot("screenshots/limpeza_01_login_sucesso.png")
    # -----------------------------------------------

except Exception as e:
    print(f"❌ Erro ao fazer login: {e}")
    # --- 4. TIRA SCREENSHOT DO ERRO NO LOGIN ---
    driver.save_screenshot("screenshots/limpeza_ERRO_LOGIN.png")
    # -------------------------------------------
    driver.quit()
    exit()

# --- Lógica de Exclusão Otimizada ---
contador_exclusoes = 0

try:
    driver.get(URL_ORDENS_SERVICO)
    print(f"Navegando para {URL_ORDENS_SERVICO} (limpeza geral)...")
    
    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
        print("Lista carregada. Iniciando exclusão em massa.")
        # --- 5. TIRA SCREENSHOT DA LISTA ANTES DE EXCLUIR ---
        driver.save_screenshot("screenshots/limpeza_02_lista_carregada.png")
        # ----------------------------------------------------
    except TimeoutException:
        print("A tabela não carregou ou a lista já está vazia.")
        driver.save_screenshot("screenshots/limpeza_03_lista_vazia.png")
        pass

    while True:
        try:
            botao_remover = wait_curto.until(
                EC.element_to_be_clickable((By.XPATH, "(//a[@title='Excluir'])[1]"))
            )
            time.sleep(1) 
            botao_remover.click()
            
            botao_confirmar = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Sim, excluir')]"))
            )
            botao_confirmar.click()

            wait.until(
                EC.invisibility_of_element_located((By.XPATH, "//button[contains(., 'Sim, excluir')]"))
            )
            
            contador_exclusoes += 1
            print(f"✅ Ordens (geral) excluídas: {contador_exclusoes}", end="\r")

        except TimeoutException:
            print(f"\n\nNenhum botão 'Excluir' encontrado.")
            print("A lista de ordens de serviço (geral) parece estar vazia.")
            # --- 6. TIRA SCREENSHOT QUANDO FINALIZA ---
            driver.save_screenshot("screenshots/limpeza_04_finalizado_sucesso.png")
            # -----------------------------------------
            break 
        
        except (StaleElementReferenceException, ElementClickInterceptedException):
            print("♻️ A página está recarregando, tentando novamente...", end="\r")
            continue 

        except Exception as e:
            print(f"\n❌ Ocorreu um erro inesperado: {e}")
            # --- 7. TIRA SCREENSHOT DE QUALQUER ERRO INESPERADO ---
            # (Usamos o tempo para garantir um nome de arquivo único)
            timestamp = int(time.time())
            driver.save_screenshot(f"screenshots/limpeza_ERRO_INESPERADO_{timestamp}.png")
            # --------------------------------------------------------
            
            print("Atualizando a página (F5) e tentando continuar...")
            driver.refresh()
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
            except TimeoutException:
                print("Não foi possível recarregar a tabela. Encerrando.")
                break
            continue

except Exception as e:
    print(f"\n❌ Ocorreu um erro grave no processo: {e}")
    # --- 8. TIRA SCREENSHOT DE ERRO GRAVE ---
    timestamp = int(time.time())
    driver.save_screenshot(f"screenshots/limpeza_ERRO_GRAVE_{timestamp}.png")
    # ----------------------------------------
finally:
    driver.quit()

print(f"\n\n--- Processo de limpeza geral finalizado! ---")
print(f"Total de {contador_exclusoes} ordens de serviço (geral) excluídas.")