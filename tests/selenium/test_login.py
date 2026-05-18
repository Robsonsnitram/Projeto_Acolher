"""
Testes de Login — Projeto Acolher
Página: /src/Coordenacao.php

Formulário autentica apenas por senha (sem campo de usuário):
  Campo senha:  <input type="password" id="senha" name="senha" required>
  Botão enviar: <input type="submit" value="Entrar">
  Ação:         POST → senha.php
  Senha válida: Acolher@2025
  Sucesso:      redirect → /src/registros.php
  Falha:        alert("Senha incorreta!") + redirect → Coordenacao.php
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

SENHA_VALIDA = "Acolher@2025"
SENHA_INVALIDA = "senhaErrada!99"


def _url_login(base_url: str) -> str:
    return f"{base_url}/src/Coordenacao.php"


def _abrir_login(driver, base_url: str) -> WebDriverWait:
    driver.get(_url_login(base_url))
    return WebDriverWait(driver, 10)


class TestLogin:
    def test_login_valido_redireciona_para_registros(self, driver, base_url):
        """Senha correta deve redirecionar para registros.php."""
        wait = _abrir_login(driver, base_url)

        campo_senha = wait.until(EC.presence_of_element_located((By.ID, "senha")))
        campo_senha.clear()
        campo_senha.send_keys(SENHA_VALIDA)

        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        wait.until(EC.url_contains("registros.php"))
        assert "registros.php" in driver.current_url, (
            f"Esperava URL contendo 'registros.php', mas obteve: {driver.current_url}"
        )

    def test_login_senha_invalida_exibe_alerta(self, driver, base_url):
        """Senha errada deve exibir alerta 'Senha incorreta!' e voltar ao login."""
        wait = _abrir_login(driver, base_url)

        campo_senha = wait.until(EC.presence_of_element_located((By.ID, "senha")))
        campo_senha.clear()
        campo_senha.send_keys(SENHA_INVALIDA)

        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        # O PHP emite alert("Senha incorreta!") via script injetado
        alerta = wait.until(EC.alert_is_present())
        texto_alerta = alerta.text
        alerta.accept()

        assert "incorreta" in texto_alerta.lower() or "senha" in texto_alerta.lower(), (
            f"Alerta inesperado: '{texto_alerta}'"
        )

        # Após fechar o alerta, deve redirecionar de volta ao login
        wait.until(EC.url_contains("Coordenacao.php"))
        assert "Coordenacao.php" in driver.current_url, (
            f"Esperava voltar a Coordenacao.php, mas estava em: {driver.current_url}"
        )

    def test_login_campo_vazio_nao_submete(self, driver, base_url):
        """Formulário vazio não deve ser enviado — campo 'required' bloqueia."""
        wait = _abrir_login(driver, base_url)

        wait.until(EC.presence_of_element_located((By.ID, "senha")))

        # Clica em Entrar sem preencher a senha
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        # O atributo 'required' impede o submit; verificamos via API de validação HTML5
        campo_senha = driver.find_element(By.ID, "senha")
        eh_valido = driver.execute_script(
            "return arguments[0].validity.valid;", campo_senha
        )
        assert not eh_valido, (
            "Campo vazio deveria falhar na validação HTML5 (required), mas passou."
        )

        # Página não deve ter mudado
        assert "Coordenacao.php" in driver.current_url, (
            f"Formulário não deveria ter sido enviado. URL: {driver.current_url}"
        )
