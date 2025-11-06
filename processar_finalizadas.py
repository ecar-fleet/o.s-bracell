import time
import os  # Importado para ler variáveis de ambiente
from typing import Optional
from selenium import webdriver
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        NoSuchElementException,
                                        StaleElementReferenceException,
                                        TimeoutException)
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

URL_ORDENS_SERVICO = "https://sofitview.com.br/#/client/serviceorders?status=finished"

# --- Lendo usuário e senha dos Secrets ---
USERNAME = os.environ.get("SOFIT_USER")
PASSWORD = os.environ.get("SOFIT_PASS")

if not USERNAME or not PASSWORD:
    print("❌ Erro: Variáveis de ambiente SOFIT_USER ou SOFIT_PASS não definidas.")
    driver.quit()
    exit()
# -----------------------------------------

# ----------------- Helpers de Estabilidade -----------------
def safe_click(element):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.15)
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)

def wait_for_url_contains(fragment: str, timeout: int = 10):
    WebDriverWait(driver, timeout).until(EC.url_contains(fragment))

def get_expense_links():
    return driver.find_elements(By.XPATH, "//a[contains(@href, '#/client/expenses/') and @target='_blank']")

def get_expense_links_count() -> int:
    try:
        return len(get_expense_links())
    except Exception:
        return 0

def wait_until_expense_count_changes(previous: int, timeout: int = 10) -> bool:
    try:
        WebDriverWait(driver, timeout).until(lambda d: get_expense_links_count() != previous)
        return True
    except TimeoutException:
        return False

def click_with_retry(locator: tuple, attempts: int = 3, pause: float = 0.3):
    last_err = None
    for i in range(attempts):
        try:
            el = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(locator))
            safe_click(el)
            return True
        except (StaleElementReferenceException, ElementClickInterceptedException) as e:
            last_err = e
            time.sleep(pause)
    if last_err:
        raise last_err
    return False

def wait_until_gone(xpath: str, timeout: int = 10) -> bool:
    try:
        WebDriverWait(driver, timeout).until(lambda d: len(d.find_elements(By.XPATH, xpath)) == 0)
        return True
    except TimeoutException:
        return False

def wait_for_url_endswith(suffix: str, timeout: int = 10) -> bool:
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.current_url.rstrip('/') .endswith(suffix.rstrip('/')))
        return True
    except TimeoutException:
        return False

def wait_for_url_startswith(prefix: str, timeout: int = 10) -> bool:
    try:
        p = prefix.rstrip('/')
        WebDriverWait(driver, timeout).until(lambda d: d.current_url.rstrip('/').startswith(p))
        return True
    except TimeoutException:
        return False

try:
    driver.get("https://sofitview.com.br/#/login")
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

    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//a[contains(., 'Ordens de Serviço')]")))
    print("Dashboard carregado.")

except Exception as e:
    print(f"❌ Erro ao fazer login: {e}")
    driver.quit()
    exit()

# --- Lógica de Processamento de OS ---
contador_os_processadas = 0
last_deleted_os_id = None 

try:
    driver.get(URL_ORDENS_SERVICO)
    print(f"Navegando para {URL_ORDENS_SERVICO}...")

    # 1. Inicia o loop de processamento de OS
    while True:
        try:
            # 2. Espera a tabela de OS carregar e pega a primeira OS
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
            if last_deleted_os_id:
                for _ in range(10):
                    if wait_until_gone(f"//tbody//a[contains(@href, '/client/serviceorders/{last_deleted_os_id}')]", timeout=2):
                        break
                    time.sleep(0.8)
                    driver.get(URL_ORDENS_SERVICO)
                    time.sleep(0.5)
                    driver.refresh()
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))

            if last_deleted_os_id:
                os_xpath = f"(//tbody//a[contains(@href, '#/client/serviceorders/')][not(contains(@href, '/client/serviceorders/{last_deleted_os_id}'))])[1]"
            else:
                os_xpath = "(//tbody//a[contains(@href, '#/client/serviceorders/')])[1]"

            link_os_el = wait_curto.until(EC.element_to_be_clickable((By.XPATH, os_xpath)))
            nome_os = link_os_el.text.strip()
            os_href = link_os_el.get_attribute("href")
            link_os = os_href.split("/edit")[0]
            print(f"\n--- Processando OS: {nome_os} ---")

            driver.get(link_os + "/edit")
            contador_os_processadas += 1

        except TimeoutException:
            print(f"\nNenhum link de OS encontrado.")
            print("A lista de ordens de serviço 'finished' parece estar vazia.")
            break 
        except Exception as e:
            print(f"❌ Erro ao tentar abrir a OS: {e}")
            print("Atualizando a página e tentando novamente...")
            driver.get(URL_ORDENS_SERVICO)
            continue

        # 4. Mudar o Status (com lógica corrigida)
        try:
            status_ja_correto = False
            print("     Verificando status...")
            
            try:
                wait_curto.until(EC.presence_of_element_located((
                    By.XPATH, 
                    "//div[contains(@class, 's-select-display') and normalize-space(.) = 'Aguardando NF']"
                )))
                status_ja_correto = True
                print("     ✅ Status já está como 'Aguardando NF'. Pulando.")
            
            except TimeoutException:
                print("     Status não é 'Aguardando NF'. Iniciando alteração...")
                pass

            if not status_ja_correto:
                status_dropdown = wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH, 
                        "//div[contains(@class, 's-select-display') and normalize-space(.) = 'Terminada']"
                    ))
                )
                status_dropdown.click()

                opcao_aguardando_nf = wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH, 
                        "//div[contains(@class, 's-select-result-label') and normalize-space(.) = 'Aguardando NF']"
                    ))
                )
                time.sleep(0.5) 
                opcao_aguardando_nf.click()
                print("     Status alterado. Salvando...")

                botao_salvar = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@title='Salvar']"))
                )
                botao_salvar.click()
                time.sleep(1.5) 
                print("     ✅ Salvo.")

        except Exception as e:
            print(f"     ❌ Não foi possível alterar o status: {e}")
            print("     (O status atual pode não ser 'Terminada' ou o seletor falhou)")
            print(f"     Pulando para a próxima OS...")
            driver.get(URL_ORDENS_SERVICO) 
            continue 

        # 5. Iniciar Loop Interno (Excluir Despesas até acabar)
        print("     Iniciando exclusão de despesas...")
        contador_despesas_por_os = 0

        while True:
            try:
                driver.get(link_os)
                wait.until(EC.presence_of_element_located((By.XPATH, "//h4[contains(., 'Despesas')]")))
                time.sleep(0.2)

                count_antes = get_expense_links_count()
                if count_antes == 0:
                    print(f"     ✅ Todas as {contador_despesas_por_os} despesas foram processadas.")
                    break

                link_despesa_el = get_expense_links()[0]
                nome_despesa = link_despesa_el.text.strip()
                href_despesa = link_despesa_el.get_attribute("href")
                print(f"         -> Abrindo despesa: {nome_despesa}...")

                time.sleep(0.5)
                driver.get(href_despesa)
                wait_for_url_contains("/client/expenses/")

            except TimeoutException:
                print(f"     ✅ Todas as {contador_despesas_por_os} despesas foram processadas.")
                break
            except (StaleElementReferenceException, ElementClickInterceptedException):
                print("     ♻ Página recarregando, tentando de novo...", end="\r")
                continue

            # --- DENTRO DA PÁGINA DA DESPESA ---
            try:
                print(f"         -> Excluindo {nome_despesa}...")
                click_with_retry((By.XPATH, "//a[@title='Excluir' and contains(@class,'btn-danger')]"))
                time.sleep(0.6)

                click_with_retry((By.XPATH, "//button[contains(., 'Sim, excluir')]"))
                time.sleep(0.6)

                wait.until(EC.invisibility_of_element_located((By.XPATH, "//button[contains(., 'Sim, excluir')]")))
                
                navegou = wait_for_url_startswith(link_os, timeout=8) or wait_for_url_startswith(link_os + "/edit", timeout=5)
                if not navegou:
                    driver.get(link_os)
                
                time.sleep(0.5)
                driver.refresh()
                wait.until(EC.presence_of_element_located((By.XPATH, "//h4[contains(., 'Despesas')]")))
                if not wait_until_expense_count_changes(previous=count_antes, timeout=10):
                    time.sleep(0.8)
                
                count_depois = get_expense_links_count()
                if count_depois < count_antes:
                    contador_despesas_por_os += 1
                    print(f"         -> Despesa '{nome_despesa}' excluída. Restantes: {count_depois}.")
                else:
                    print("         ⚠ A contagem de despesas não reduziu; tentando novamente no próximo ciclo.")
                time.sleep(0.3)
            except Exception as e:
                print(f"         ❌ Erro ao tentar excluir a despesa {nome_despesa}: {e}")
                driver.get(link_os)
                time.sleep(0.5)

        # 17. Após terminar despesas, excluir a própria OS
        try:
            print("     Excluindo a OS...")
            driver.get(link_os)
            wait.until(EC.presence_of_element_located((By.XPATH, "//h4[contains(., 'Despesas')]")))
            if get_expense_links_count() > 0:
                print("     ⚠ Ainda existem despesas. Voltando ao loop de despesas.")
                continue
            
            driver.get(link_os)
            click_with_retry((By.XPATH, "//a[@title = 'Excluir']"))
            click_with_retry((By.XPATH, "//button[contains(., 'Sim, excluir')]"))
            
            time.sleep(1)
            driver.get(URL_ORDENS_SERVICO)
            time.sleep(0.8)
            driver.refresh()
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
            
            try:
                os_id = link_os.rstrip('/').split('/')[-1]
                wait_until_gone(f"//tbody//a[contains(@href, '/client/serviceorders/{os_id}')]", timeout=20)
                last_deleted_os_id = os_id
            except Exception:
                pass
            print("     ✅ OS excluída com sucesso.")
        except Exception as e:
            print(f"     ❌ Não foi possível excluir a OS: {e}")
            driver.get(URL_ORDENS_SERVICO)
        
        print(f"     Processo da OS {nome_os} concluído. Voltando para a lista principal.")
        time.sleep(1)
        
except Exception as e:
    print(f"\n❌ Ocorreu um erro grave no processo: {e}")
finally:
    # Garante que o driver será fechado no final
    driver.quit()

# --- Fim do Script ---
print(f"\n\n--- Processo finalizado! ---")
print(f"Total de {contador_os_processadas} ordens de serviço processadas.")