"""
Cliente de leitura do portal Vedrano (consultaleituras.vedrano.com.br).

Este portal é uma SPA de terceiros sem API pública documentada, então o login e a
extração de dados são feitos via automação de navegador (Playwright), com duas
estratégias combinadas para achar as leituras de consumo:

1. Interceptar as respostas de rede (XHR/fetch) que a própria SPA faz para buscar
   os dados — é o método mais confiável porque não depende da estrutura visual da
   página, só do formato JSON que o backend do Vedrano devolve.
2. Fallback: raspar tabelas HTML renderizadas procurando por padrões de
   data + número (m³/litros).

Como este ambiente de desenvolvimento não tem acesso de rede ao domínio do
Vedrano, os seletores usados no login são heurísticos (tentam vários padrões
comuns de formulário) e não puderam ser validados contra o site real. Rode com
VEDRANO_DEBUG=1 na primeira vez: se o login ou a extração falhar, o cliente salva
screenshot + HTML + JSON capturado em backend/debug_vedrano/ para diagnóstico.
"""
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_LOGIN_URL = "https://consultaleituras.vedrano.com.br/login-externo"
DEBUG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "debug_vedrano")

# Seletores candidatos, em ordem de tentativa, para cada campo do formulário de login.
LOGIN_FIELD_SELECTORS = [
    "input[name*='login' i]", "input[id*='login' i]", "input[placeholder*='login' i]",
    "input[name*='usuario' i]", "input[id*='usuario' i]", "input[placeholder*='usuário' i]",
    "input[type='text']", "input[type='email']",
]
PASSWORD_FIELD_SELECTORS = [
    "input[type='password']", "input[name*='senha' i]", "input[id*='senha' i]",
]
SUBMIT_SELECTORS = [
    "button[type='submit']", "text=Entrar", "text=Acessar", "text=Login", "text=Login",
]
CONSUMPTION_NAV_SELECTORS = [
    "text=/consumo/i", "text=/leitura/i", "text=/histórico/i", "text=/diári[ao]/i",
]

DATE_KEY_RE = re.compile(r"data|date|dia|leitura", re.IGNORECASE)
VALUE_KEY_RE = re.compile(r"consumo|litro|volume|m3|m³|valor|leitura", re.IGNORECASE)


@dataclass
class RawReading:
    reading_date: date
    consumo_m3: float


class VedranoLoginError(RuntimeError):
    pass


class VedranoClient:
    def __init__(
        self,
        login: str,
        senha: str,
        login_url: str = DEFAULT_LOGIN_URL,
        debug: bool = False,
    ):
        self.login = login
        self.senha = senha
        self.login_url = login_url
        self.debug = debug
        self._captured_json: list[object] = []

    def fetch_readings(self) -> list[RawReading]:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        if self.debug:
            os.makedirs(DEBUG_DIR, exist_ok=True)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(locale="pt-BR")
            page = context.new_page()
            page.on("response", self._capture_json_response)

            try:
                page.goto(self.login_url, wait_until="networkidle", timeout=30000)
                self._do_login(page)
                self._go_to_consumption_view(page)
                page.wait_for_timeout(2500)  # dá tempo pras XHRs de dados terminarem
            except PWTimeout as e:
                self._save_debug(page, "timeout")
                raise VedranoLoginError(f"Timeout navegando o portal Vedrano: {e}") from e
            except Exception:
                self._save_debug(page, "error")
                raise
            else:
                if self.debug:
                    self._save_debug(page, "ok")

            readings = self._extract_from_captured_json()
            if not readings:
                readings = self._extract_from_dom(page)

            browser.close()

        return readings

    def _do_login(self, page) -> None:
        user_field = self._first_visible(page, LOGIN_FIELD_SELECTORS)
        pass_field = self._first_visible(page, PASSWORD_FIELD_SELECTORS)
        if not user_field or not pass_field:
            raise VedranoLoginError(
                "Não encontrei os campos de login/senha no portal Vedrano. "
                "Rode com VEDRANO_DEBUG=1 e ajuste os seletores em vedrano_client.py "
                "com base no HTML salvo em debug_vedrano/."
            )
        user_field.fill(self.login)
        pass_field.fill(self.senha)

        submit = self._first_visible(page, SUBMIT_SELECTORS)
        if submit:
            submit.click()
        else:
            pass_field.press("Enter")

        page.wait_for_load_state("networkidle", timeout=20000)

        if page.query_selector("input[type='password']"):
            # Ainda numa tela com campo de senha visível → login provavelmente falhou.
            raise VedranoLoginError(
                "Login no portal Vedrano não foi confirmado (ainda há campo de senha na tela). "
                "Verifique VEDRANO_LOGIN / VEDRANO_SENHA."
            )

    def _go_to_consumption_view(self, page) -> None:
        nav = self._first_visible(page, CONSUMPTION_NAV_SELECTORS)
        if nav:
            nav.click()
            page.wait_for_load_state("networkidle", timeout=20000)

    @staticmethod
    def _first_visible(page, selectors: list[str]):
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    return el
            except Exception:
                continue
        return None

    def _capture_json_response(self, response) -> None:
        try:
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                return
            data = response.json()
            self._captured_json.append(data)
        except Exception:
            pass

    def _extract_from_captured_json(self) -> list[RawReading]:
        readings: dict[date, float] = {}
        for blob in self._captured_json:
            for record in _iter_dicts(blob):
                reading = _dict_to_reading(record)
                if reading:
                    readings[reading.reading_date] = reading.consumo_m3
        return [RawReading(d, v) for d, v in sorted(readings.items())]

    def _extract_from_dom(self, page) -> list[RawReading]:
        readings: dict[date, float] = {}
        rows = page.query_selector_all("table tr")
        for row in rows:
            text = row.inner_text()
            reading = _text_row_to_reading(text)
            if reading:
                readings[reading.reading_date] = reading.consumo_m3
        return [RawReading(d, v) for d, v in sorted(readings.items())]

    def _save_debug(self, page, tag: str) -> None:
        if not self.debug:
            return
        try:
            page.screenshot(path=os.path.join(DEBUG_DIR, f"{tag}.png"), full_page=True)
            with open(os.path.join(DEBUG_DIR, f"{tag}.html"), "w", encoding="utf-8") as f:
                f.write(page.content())
            with open(os.path.join(DEBUG_DIR, f"{tag}_captured.json"), "w", encoding="utf-8") as f:
                json.dump(self._captured_json, f, ensure_ascii=False, indent=2, default=str)
            logger.info("Debug do Vedrano salvo em %s (%s)", DEBUG_DIR, tag)
        except Exception as e:
            logger.warning("Falha salvando debug do Vedrano: %s", e)


def _iter_dicts(obj):
    """Percorre recursivamente um JSON arbitrário produzindo todos os dicts encontrados."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_dicts(item)


def _dict_to_reading(record: dict) -> Optional[RawReading]:
    if not isinstance(record, dict):
        return None
    date_val, value_val, value_key = None, None, ""
    for key, val in record.items():
        if date_val is None and DATE_KEY_RE.search(key) and isinstance(val, (str, int, float)):
            d = _parse_any_date(val)
            if d:
                date_val = d
        if value_val is None and VALUE_KEY_RE.search(key) and isinstance(val, (int, float)):
            value_val = float(val)
            value_key = key
    if date_val is None or value_val is None:
        return None
    return RawReading(date_val, _normalize_to_m3(value_val, value_key))


def _text_row_to_reading(text: str) -> Optional[RawReading]:
    d = _parse_any_date(text)
    if not d:
        return None
    m = re.search(r"(\d+[.,]?\d*)\s*(m³|m3|litros?|l\b)", text, re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    return RawReading(d, _normalize_to_m3(value, m.group(2)))


def _parse_any_date(val) -> Optional[date]:
    if isinstance(val, (int, float)):
        try:
            # timestamp em ms ou s
            ts = val / 1000 if val > 10_000_000_000 else val
            return datetime.fromtimestamp(ts).date()
        except Exception:
            return None
    if not isinstance(val, str):
        return None
    for pattern, parser in (
        (r"(\d{4})-(\d{2})-(\d{2})", lambda m: date(int(m[1]), int(m[2]), int(m[3]))),
        (r"(\d{2})/(\d{2})/(\d{4})", lambda m: date(int(m[3]), int(m[2]), int(m[1]))),
    ):
        m = re.search(pattern, val)
        if m:
            try:
                return parser(m)
            except ValueError:
                continue
    return None


def _normalize_to_m3(value: float, unit_hint: str) -> float:
    unit_hint = unit_hint.lower()
    if "litro" in unit_hint or unit_hint == "l" or "l" == unit_hint.strip():
        return value / 1000
    if "m3" in unit_hint or "m³" in unit_hint or "metro" in unit_hint:
        return value
    # Sem unidade explícita: heurística — consumo diário de água residencial
    # raramente passa de ~5 m³/dia por apto, então valores grandes são litros.
    return value / 1000 if value > 50 else value
