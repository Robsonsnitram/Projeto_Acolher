"""
Testes de Consulta de CEP (ViaCEP) — Projeto Acolher
Página: /src/Agendamento.php

Campo CEP:  <input id="cep" name="cep-paciente" onblur="pesquisacep(this.value);" maxlength="9">
Campos de endereço preenchidos pela API:
  #rua    → logradouro
  #bairro → bairro
  #cidade → localidade
  #uf     → uf

Fluxo da integração (JSONP client-side):
  1. onblur dispara pesquisacep(valor)
  2. Se o formato for inválido → alert("Formato de CEP inválido.")
  3. Se o formato for válido   → injeta <script src="viacep.com.br/ws/{CEP}/json/?callback=meu_callback">
  4. meu_callback() preenche os campos ou exibe alert("CEP não encontrado.")

Simulação de falha de comunicação:
  Utilizamos o Chrome DevTools Protocol (CDP) Network.setBlockedURLs para
  bloquear as requisições ao viacep.com.br antes do teste, simulando timeout /
  indisponibilidade da API. O callback JSONP nunca é chamado, deixando os
  campos com o placeholder "..." indefinidamente.
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# CEP real e conhecido para teste de sucesso (Av. Paulista, São Paulo – SP)
CEP_VALIDO      = "01310100"
CEP_INEXISTENTE = "99999999"   # não existe na base dos Correios
CEP_FORMATO_INVALIDO = "1234"  # menos de 8 dígitos → formato inválido

TIMEOUT_CAMPOS = 15  # segundos para aguardar preenchimento pela API


def _abrir_agendamento(driver, base_url: str) -> WebDriverWait:
    driver.get(f"{base_url}/src/Agendamento.php")
    return WebDriverWait(driver, TIMEOUT_CAMPOS)


def _digitar_cep_e_sair_do_campo(driver, wait, cep: str):
    """Preenche o campo CEP e sai (Tab), disparando o evento onblur."""
    campo_cep = wait.until(EC.presence_of_element_located((By.ID, "cep")))
    campo_cep.clear()
    campo_cep.send_keys(cep)
    campo_cep.send_keys(Keys.TAB)  # dispara onblur → pesquisacep()
    return campo_cep


class TestCEP:
    # ------------------------------------------------------------------ #
    #  CEP VÁLIDO → preenchimento automático dos campos de endereço        #
    # ------------------------------------------------------------------ #
    def test_cep_valido_preenche_campos_de_endereco(self, driver, base_url):
        """
        CEP 01310-100 (Av. Paulista, SP) deve preencher rua, bairro,
        cidade e UF automaticamente via ViaCEP.
        """
        wait = _abrir_agendamento(driver, base_url)
        _digitar_cep_e_sair_do_campo(driver, wait, CEP_VALIDO)

        # Aguarda até a cidade ter valor real (sai do estado "..." ou "")
        wait.until(
            lambda d: d.find_element(By.ID, "cidade").get_attribute("value")
            not in ("", "...")
        )

        cidade = driver.find_element(By.ID, "cidade").get_attribute("value")
        uf     = driver.find_element(By.ID, "uf").get_attribute("value")
        rua    = driver.find_element(By.ID, "rua").get_attribute("value")
        bairro = driver.find_element(By.ID, "bairro").get_attribute("value")

        assert cidade == "São Paulo", f"Cidade esperada: 'São Paulo', obtida: '{cidade}'"
        assert uf == "SP",            f"UF esperada: 'SP', obtida: '{uf}'"
        assert "Paulista" in rua,     f"Rua deveria conter 'Paulista', obtida: '{rua}'"
        assert bairro != "",          f"Bairro não foi preenchido"

    # ------------------------------------------------------------------ #
    #  CEP COM FORMATO INVÁLIDO → alert de formato                        #
    # ------------------------------------------------------------------ #
    def test_cep_formato_invalido_exibe_alerta(self, driver, base_url):
        """
        CEP com menos de 8 dígitos deve disparar alert 'Formato de CEP inválido.'
        (validação feita em pesquisacep() antes de chamar a API).
        """
        wait = _abrir_agendamento(driver, base_url)
        _digitar_cep_e_sair_do_campo(driver, wait, CEP_FORMATO_INVALIDO)

        alerta = wait.until(EC.alert_is_present())
        texto = alerta.text
        alerta.accept()

        assert "inválido" in texto.lower() or "formato" in texto.lower(), (
            f"Alert inesperado para CEP de formato inválido: '{texto}'"
        )

    # ------------------------------------------------------------------ #
    #  CEP INEXISTENTE → alert de CEP não encontrado                      #
    # ------------------------------------------------------------------ #
    def test_cep_inexistente_exibe_alerta_nao_encontrado(self, driver, base_url):
        """
        CEP 99999-999 não existe na base ViaCEP e deve retornar
        alert 'CEP não encontrado.' via meu_callback().
        """
        wait = _abrir_agendamento(driver, base_url)
        _digitar_cep_e_sair_do_campo(driver, wait, CEP_INEXISTENTE)

        alerta = wait.until(EC.alert_is_present())
        texto = alerta.text
        alerta.accept()

        assert "encontrado" in texto.lower() or "não" in texto.lower(), (
            f"Alert inesperado para CEP inexistente: '{texto}'"
        )

    # ------------------------------------------------------------------ #
    #  SIMULAÇÃO DE FALHA DE COMUNICAÇÃO COM A API (mock via CDP)         #
    # ------------------------------------------------------------------ #
    def test_cep_falha_de_comunicacao_campos_nao_preenchidos(self, driver, base_url):
        """
        Simula indisponibilidade da API ViaCEP bloqueando as requisições
        via Chrome DevTools Protocol (Network.setBlockedURLs).
        O callback JSONP nunca é invocado, portanto os campos de endereço
        devem permanecer com o placeholder '...' (estado de loading) ou vazios.
        """
        wait = _abrir_agendamento(driver, base_url)

        # Ativa bloqueio de rede para viacep.com.br antes de digitar o CEP
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd(
            "Network.setBlockedURLs",
            {"urls": ["*viacep.com.br*"]}
        )

        try:
            _digitar_cep_e_sair_do_campo(driver, wait, CEP_VALIDO)

            # Aguarda tempo suficiente para a tentativa de requisição falhar
            time.sleep(4)

            cidade = driver.find_element(By.ID, "cidade").get_attribute("value")
            rua    = driver.find_element(By.ID, "rua").get_attribute("value")

            # Com a API bloqueada, os campos devem permanecer no placeholder
            # de loading ("...") ou vazios — nunca com dados reais.
            dados_reais_nao_carregados = cidade in ("...", "", None) or (
                "São Paulo" not in cidade
            )
            assert dados_reais_nao_carregados, (
                "API bloqueada, mas os campos foram preenchidos com dados reais. "
                f"Cidade: '{cidade}', Rua: '{rua}'"
            )

        finally:
            # Remove o bloqueio para não afetar os próximos testes
            driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": []})
            driver.execute_cdp_cmd("Network.disable", {})
