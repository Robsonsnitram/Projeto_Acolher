"""
Selenium + captura automatica de screenshots por acao e por teste.

Estrutura gerada em prints/:
  prints/
    <nome_do_teste>/
      000_inicio.png          <- estado da tela ao entrar no teste
      001_antes_navegar.png   <- antes de driver.get()
      002_apos_navegar.png    <- apos carregar a pagina
      003_antes_click.png     <- antes de clicar num elemento
      004_apos_click.png      <- apos o clique
      005_antes_digitar.png   <- antes de send_keys()
      006_apos_digitar.png    <- apos send_keys()
      ...                     <- demais acoes na mesma sequencia
      999_fim.png             <- estado da tela ao sair do teste
      FALHA.png               <- capturado apenas em caso de falha
    terminal_pytest_resultado.png  <- imagem com o resultado final do pytest

Abordagem: subclasse de webdriver.Chrome (ScreenshotChrome) + subclasse de
WebElement (ScreenshotWebElement). Isso evita os problemas do EventFiringWebDriver,
que re-propaga UnexpectedAlertPresentException dentro do click(), quebrando testes
que verificam alertas disparados por cliques.
"""

import re
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont
from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "http://localhost/Acolher"
PRINTS_DIR = Path(__file__).parent / "prints"


# -----------------------------------------------------------------------------
#  WebElement instrumentado: screenshots antes/depois de click e send_keys
# -----------------------------------------------------------------------------

class ScreenshotWebElement(WebElement):
    """
    Subclasse de WebElement que tira prints automaticamente antes e depois
    de click() e send_keys(). UnexpectedAlertPresentException e tratada
    localmente para nao quebrar testes que esperam alertas.
    """

    _drv: "ScreenshotChrome | None" = None  # injetado por wrap()

    @classmethod
    def wrap(cls, element: WebElement, drv: "ScreenshotChrome") -> "ScreenshotWebElement":
        """Encapsula um WebElement copiando seus atributos de instancia."""
        obj = object.__new__(cls)
        obj.__dict__.update(element.__dict__)
        obj._drv = drv
        return obj

    # -- acoes instrumentadas -------------------------------------------------

    def click(self) -> None:
        if self._drv:
            self._drv._shot("antes_click")
        alert_apareceu = False
        try:
            super().click()
        except UnexpectedAlertPresentException:
            alert_apareceu = True  # alerta bloqueou o comando; nao tentar screenshot
        # So tira apos_click se nao ha alerta ativo (evita auto-dismiss pelo Chrome)
        if self._drv and not alert_apareceu:
            self._drv._shot("apos_click")

    def send_keys(self, *value) -> None:
        if self._drv:
            self._drv._shot("antes_digitar")
        alert_apareceu = False
        try:
            super().send_keys(*value)
        except UnexpectedAlertPresentException:
            alert_apareceu = True  # onblur disparou alert(); nao tentar screenshot
        if self._drv and not alert_apareceu:
            self._drv._shot("apos_digitar")


# -----------------------------------------------------------------------------
#  Chrome instrumentado: screenshots em get() e find_element()
# -----------------------------------------------------------------------------

class ScreenshotChrome(webdriver.Chrome):
    """
    Subclasse de Chrome que:
      - captura screenshot antes e depois de get() (navegacao)
      - retorna ScreenshotWebElement em find_element/find_elements
      - expoe _shot() para uso interno pelo ScreenshotWebElement
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._shots_dir: Path = PRINTS_DIR
        self._counter: int = 0

    def set_test_dir(self, directory: Path) -> None:
        """Chamado no inicio de cada teste para redirecionar os prints."""
        self._shots_dir = directory
        self._counter = 0
        directory.mkdir(parents=True, exist_ok=True)

    def _shot(self, label: str) -> None:
        """Salva um screenshot numerado; suprime todas as excecoes."""
        self._counter += 1
        path = self._shots_dir / f"{self._counter:03d}_{label}.png"
        try:
            super().save_screenshot(str(path))
        except Exception:
            pass  # nao interrompe o teste por falha no screenshot

    # -- navegacao ------------------------------------------------------------

    def get(self, url: str) -> None:
        self._shot("antes_navegar")
        super().get(url)
        self._shot("apos_navegar")

    # -- busca de elementos ---------------------------------------------------

    def find_element(self, by, value) -> ScreenshotWebElement:
        element = super().find_element(by, value)
        return ScreenshotWebElement.wrap(element, self)

    def find_elements(self, by, value) -> list:
        elements = super().find_elements(by, value)
        return [ScreenshotWebElement.wrap(e, self) for e in elements]


# -----------------------------------------------------------------------------
#  Fixtures pytest
# -----------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default=BASE_URL,
        help="URL base do sistema Acolher (padrao: http://localhost/Acolher)",
    )


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url").rstrip("/")


@pytest.fixture(scope="session")
def prints_dir():
    PRINTS_DIR.mkdir(exist_ok=True)
    return PRINTS_DIR


@pytest.fixture(scope="session")
def driver(prints_dir):
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-popup-blocking")
    # options.add_argument("--headless=new")  # descomente para CI/CD
    # "ignore" faz o Chrome nao auto-dismissar alertas quando um comando WebDriver falha,
    # garantindo que os testes que usam wait.until(EC.alert_is_present()) funcionem corretamente.
    options.set_capability("unhandledPromptBehavior", "ignore")

    service = Service(ChromeDriverManager().install())
    drv = ScreenshotChrome(service=service, options=options)
    drv.implicitly_wait(10)
    drv.set_page_load_timeout(30)

    yield drv
    drv.quit()


@pytest.fixture(autouse=True)
def _screenshots_por_teste(driver, prints_dir, request):
    """
    Para cada teste:
      1. Cria subpasta em prints/ com o nome do caso de teste
      2. Salva 000_inicio.png (estado da tela ao entrar)
      3. Executa o teste (yield)
      4. Salva 999_fim.png (estado da tela ao sair)
    """
    safe = re.sub(r"[^\w]", "_", request.node.nodeid).strip("_")
    safe = re.sub(r"_+", "_", safe)[:80]

    test_dir = prints_dir / safe
    test_dir.mkdir(exist_ok=True)
    driver.set_test_dir(test_dir)

    try:
        driver.save_screenshot(str(test_dir / "000_inicio.png"))
    except Exception:
        pass

    yield

    try:
        driver.save_screenshot(str(test_dir / "999_fim.png"))
    except Exception:
        pass


# -----------------------------------------------------------------------------
#  Hook de falha: FALHA.png
# -----------------------------------------------------------------------------

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        try:
            drv = item.funcargs.get("driver")
            pdir = item.funcargs.get("prints_dir")
            if drv and pdir:
                safe = re.sub(r"[^\w]", "_", item.nodeid).strip("_")
                safe = re.sub(r"_+", "_", safe)[:80]
                test_dir = pdir / safe
                test_dir.mkdir(exist_ok=True)
                drv.save_screenshot(str(test_dir / "FALHA.png"))
        except Exception:
            pass


# -----------------------------------------------------------------------------
#  Imagem do terminal ao encerrar a sessao
# -----------------------------------------------------------------------------

_relatorios: list = []


def pytest_runtest_logreport(report) -> None:
    """Coleta resultado de cada teste para gerar a imagem final."""
    if report.when == "call":
        _relatorios.append(report)


def _render_terminal(lines: list[str], output: Path) -> None:
    """Converte linhas de texto em PNG com visual de terminal escuro."""
    FONT_SIZE = 14
    PADDING = 22
    BG = (15, 15, 15)
    FG = (204, 204, 204)

    font = None
    for fp in (
        "C:/Windows/Fonts/consola.ttf",   # Consolas (melhor)
        "C:/Windows/Fonts/lucon.ttf",     # Lucida Console
        "C:/Windows/Fonts/cour.ttf",      # Courier New
    ):
        if Path(fp).exists():
            try:
                font = ImageFont.truetype(fp, FONT_SIZE)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default(size=FONT_SIZE)

    try:
        bb = font.getbbox("X")
        char_w, char_h = bb[2] - bb[0], bb[3] - bb[1]
    except Exception:
        char_w, char_h = FONT_SIZE // 2, FONT_SIZE

    line_h = char_h + 6
    max_chars = max((len(l) for l in lines), default=60)
    width = max(960, max_chars * char_w + PADDING * 2)
    height = len(lines) * line_h + PADDING * 2

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    COLORS = {
        "PASSOU": (80, 210, 80),
        "FALHOU": (220, 70, 70),
        "passed": (80, 210, 80),
        "failed": (220, 70, 70),
        "=":      (90, 150, 255),
    }

    for i, line in enumerate(lines):
        y = PADDING + i * line_h
        color = FG
        for key, clr in COLORS.items():
            if key in line:
                color = clr
                break
        draw.text((PADDING, y), line, font=font, fill=color)

    img.save(str(output))


def pytest_sessionfinish(session, exitstatus) -> None:
    """Gera a imagem PNG com o resultado consolidado dos testes."""
    PRINTS_DIR.mkdir(exist_ok=True)

    n_pass = sum(1 for r in _relatorios if r.passed)
    n_fail = sum(1 for r in _relatorios if r.failed)
    now = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
    SEP = "-" * 80

    lines = [
        "=" * 80,
        "  Projeto Acolher  -  Testes Automatizados Selenium + pytest",
        f"  Executado em: {now}",
        "=" * 80,
        "",
    ]

    modulo_ant = None
    for r in _relatorios:
        partes = r.nodeid.split("::")
        modulo = partes[0].replace(".py", "")
        nome   = partes[-1]
        status = "PASSOU  [OK]" if r.passed else "FALHOU  [!!]"

        if modulo != modulo_ant:
            if modulo_ant is not None:
                lines.append("")
            lines.append(f"  >> {modulo}")
            lines.append(f"  {SEP[:76]}")
            modulo_ant = modulo

        lines.append(f"     {nome:<62}  {status}")

    lines += [
        "",
        "=" * 80,
        f"  Total: {len(_relatorios)} testes  |  {n_pass} passaram  |  {n_fail} falharam",
        f"  Exit code: {exitstatus}",
        "=" * 80,
    ]

    out = PRINTS_DIR / "terminal_pytest_resultado.png"
    _render_terminal(lines, out)
    print(f"\n  [PRINTS] Terminal salvo: {out}")
