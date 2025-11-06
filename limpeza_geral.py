import time
import os  # Importado
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
# -------------------------------------------

driver = webdriver.Chrome(options=options)

# Esperas
wait = WebDriverWait(driver, 20)
wait_curto = WebDriverWait(driver, 3)

# URL alterada para a raiz, para limpar o que sobrou
URL_ORDENS_SERVICO = "https://sofitview.com.br/#/client/serviceorders"

# --- Lendo usuário e senha dos Secrets ---
USERNAME = os.environ.get("SOFIT_USER")
PASSWORD = os.environ.get("SOFIT_PASS")

if not USERNAME or not PASSWORD:
    print("❌ Erro: Variáveis de ambiente SOFIT_USER ou SOFIT_PASS não definidas.")
    driver.quit()
    exit()
# -----------------------------------------

driver.get("https://sofitview.com.br/#/login")

try:
    print("Tentando fazer login...")
    campo_usuario = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//input[@placeholder='Informe seu usuário']")))
    campo_usuario.send_keys(USERNAME) # Modificado

    campo_senha = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//input[@type='password']")))
    campo_senha.send_keys(PASSWORD) # Modificado

    botao_login = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//button[contains(., 'Fazer login')]")))
    botao_login.click()
    print("✅ Login feito com sucesso!")

except Exception as e:
    print(f"❌ Erro ao fazer login: {e}")
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
    except TimeoutException:
        print("A tabela não carregou ou a lista já está vazia.")
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
            break 
        
        except (StaleElementReferenceException, ElementClickInterceptedException):
            print("♻️ A página está recarregando, tentando novamente...", end="\r")
            continue 

        except Exception as e:
            print(f"\n❌ Ocorreu um erro inesperado: {e}")
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
finally:
    # Garante que o driver será fechado no final
    driver.quit()

# --- Fim do Script ---
print(f"\n\n--- Processo de limpeza geral finalizado! ---")
print(f"Total de {contador_exclusoes} ordens de serviço (geral) excluídas.")