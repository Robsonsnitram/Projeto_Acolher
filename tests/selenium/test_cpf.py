"""
Testes de Validação de CPF — Projeto Acolher
Página: /src/Agendamento.php

Campo CPF:  <input name="CPF-paciente" type="text" placeholder="Insira seu CPF">
Botão:      <button class="teste_cpf" onclick="testarCPF()">Testar CPF</button>

O botão dispara uma requisição AJAX (fetch) para /tests/validaCPF.php e exibe
o resultado em um alert():
  Sucesso:  "✅ CPF válido"
  Falha:    "❌ CPF inválido"
  Vazio:    "Digite um CPF para testar!"

CPFs válidos usados nos testes foram verificados pelo algoritmo mod-11 (dois
dígitos verificadores), que é o mesmo implementado em validaCPF.php.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- CPFs válidos (verificados pelo algoritmo mod-11) ---
CPF_VALIDO_1 = "52998224725"   # 529.982.247-25
CPF_VALIDO_2 = "11144477735"   # 111.444.777-35

# --- CPFs inválidos ---
CPF_DIGITOS_ERRADOS = "12345678900"  # dígito verificador incorreto
CPF_TODOS_IGUAIS    = "11111111111"  # sequência repetida, rejeitada antes do mod-11

# --- Entradas mal formatadas ---
CPF_CURTO   = "1234567"          # menos de 11 dígitos
CPF_LETRAS  = "abcdefghijk"      # apenas letras
CPF_SIMBOLOS = "###.###.###-##"  # apenas símbolos


def _abrir_agendamento(driver, base_url: str) -> WebDriverWait:
    driver.get(f"{base_url}/src/Agendamento.php")
    return WebDriverWait(driver, 10)


def _preencher_e_testar_cpf(driver, wait, valor_cpf: str) -> str:
    """Preenche o campo CPF, clica em 'Testar CPF' e retorna o texto do alert."""
    campo = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[name='CPF-paciente']")
        )
    )
    campo.clear()
    campo.send_keys(valor_cpf)

    driver.find_element(By.CSS_SELECTOR, "button.teste_cpf").click()

    alerta = wait.until(EC.alert_is_present())
    texto = alerta.text
    alerta.accept()
    return texto


class TestCPF:
    # ------------------------------------------------------------------ #
    #  CPFs VÁLIDOS                                                        #
    # ------------------------------------------------------------------ #
    def test_cpf_valido_1(self, driver, base_url):
        """CPF 529.982.247-25 deve ser aceito como válido."""
        wait = _abrir_agendamento(driver, base_url)
        resultado = _preencher_e_testar_cpf(driver, wait, CPF_VALIDO_1)
        assert "válido" in resultado.lower(), (
            f"CPF {CPF_VALIDO_1}: resposta inesperada → '{resultado}'"
        )

    def test_cpf_valido_2(self, driver, base_url):
        """CPF 111.444.777-35 deve ser aceito como válido."""
        wait = _abrir_agendamento(driver, base_url)
        resultado = _preencher_e_testar_cpf(driver, wait, CPF_VALIDO_2)
        assert "válido" in resultado.lower(), (
            f"CPF {CPF_VALIDO_2}: resposta inesperada → '{resultado}'"
        )

    # ------------------------------------------------------------------ #
    #  CPFs INVÁLIDOS                                                      #
    # ------------------------------------------------------------------ #
    def test_cpf_invalido_digito_verificador_errado(self, driver, base_url):
        """CPF com dígitos verificadores incorretos deve ser rejeitado."""
        wait = _abrir_agendamento(driver, base_url)
        resultado = _preencher_e_testar_cpf(driver, wait, CPF_DIGITOS_ERRADOS)
        assert "inválido" in resultado.lower(), (
            f"CPF {CPF_DIGITOS_ERRADOS}: deveria ser inválido, obteve → '{resultado}'"
        )

    def test_cpf_invalido_todos_digitos_iguais(self, driver, base_url):
        """CPF com todos os dígitos iguais deve ser rejeitado (verificação anti-trivial)."""
        wait = _abrir_agendamento(driver, base_url)
        resultado = _preencher_e_testar_cpf(driver, wait, CPF_TODOS_IGUAIS)
        assert "inválido" in resultado.lower(), (
            f"CPF {CPF_TODOS_IGUAIS}: deveria ser inválido, obteve → '{resultado}'"
        )

    # ------------------------------------------------------------------ #
    #  ENTRADAS MAL FORMATADAS                                             #
    # ------------------------------------------------------------------ #
    def test_cpf_curto_menos_de_11_digitos(self, driver, base_url):
        """CPF com menos de 11 dígitos deve ser rejeitado."""
        wait = _abrir_agendamento(driver, base_url)
        resultado = _preencher_e_testar_cpf(driver, wait, CPF_CURTO)
        assert "inválido" in resultado.lower(), (
            f"CPF '{CPF_CURTO}': deveria ser inválido, obteve → '{resultado}'"
        )

    def test_cpf_com_letras(self, driver, base_url):
        """CPF contendo apenas letras deve ser rejeitado."""
        wait = _abrir_agendamento(driver, base_url)
        resultado = _preencher_e_testar_cpf(driver, wait, CPF_LETRAS)
        assert "inválido" in resultado.lower(), (
            f"CPF '{CPF_LETRAS}': deveria ser inválido, obteve → '{resultado}'"
        )

    def test_cpf_com_simbolos(self, driver, base_url):
        """CPF contendo apenas símbolos deve ser rejeitado."""
        wait = _abrir_agendamento(driver, base_url)
        resultado = _preencher_e_testar_cpf(driver, wait, CPF_SIMBOLOS)
        assert "inválido" in resultado.lower(), (
            f"CPF '{CPF_SIMBOLOS}': deveria ser inválido, obteve → '{resultado}'"
        )

    def test_cpf_campo_vazio_exige_preenchimento(self, driver, base_url):
        """Botão 'Testar CPF' com campo vazio deve alertar para digitar um CPF."""
        wait = _abrir_agendamento(driver, base_url)

        # Garante que o campo está vazio
        campo = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='CPF-paciente']")
            )
        )
        campo.clear()

        driver.find_element(By.CSS_SELECTOR, "button.teste_cpf").click()

        alerta = wait.until(EC.alert_is_present())
        texto = alerta.text
        alerta.accept()

        assert "cpf" in texto.lower() or "digit" in texto.lower(), (
            f"Alerta inesperado para campo vazio: '{texto}'"
        )
