"""Cálculo do valor da conta de água a partir de uma tabela de tarifas progressivas."""
import json
import os
from dataclasses import dataclass, field

_TARIFF_PATH = os.path.join(os.path.dirname(__file__), "sabesp_tarifas.json")


@dataclass
class TierBreakdown:
    ate_m3: float | None
    m3_na_faixa: float
    tarifa_agua_m3: float
    tarifa_esgoto_m3: float
    valor_agua: float
    valor_esgoto: float


@dataclass
class WaterBill:
    consumo_m3: float
    valor_agua: float
    valor_esgoto: float
    taxa_fixa: float
    valor_total: float
    faixas: list[TierBreakdown] = field(default_factory=list)
    configurado: bool = True
    categoria: str = ""


def load_tariff_config(path: str = _TARIFF_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def calcular_conta(consumo_m3: float, config: dict | None = None) -> WaterBill:
    """Aplica a tarifa progressiva: cada faixa é cobrada apenas pelos m³ que caem dentro dela."""
    if config is None:
        config = load_tariff_config()

    faixas_config = config["faixas"]
    restante = max(consumo_m3, 0.0)
    piso = 0.0
    faixas: list[TierBreakdown] = []
    valor_agua = 0.0
    valor_esgoto = 0.0

    for faixa in faixas_config:
        teto = faixa["ate_m3"]
        largura_faixa = (teto - piso) if teto is not None else restante
        m3_na_faixa = max(0.0, min(restante, largura_faixa))

        tarifa_agua = faixa["tarifa_agua_m3"]
        tarifa_esgoto = faixa["tarifa_esgoto_m3"]
        v_agua = m3_na_faixa * tarifa_agua
        v_esgoto = m3_na_faixa * tarifa_esgoto

        faixas.append(TierBreakdown(
            ate_m3=teto,
            m3_na_faixa=round(m3_na_faixa, 3),
            tarifa_agua_m3=tarifa_agua,
            tarifa_esgoto_m3=tarifa_esgoto,
            valor_agua=round(v_agua, 2),
            valor_esgoto=round(v_esgoto, 2),
        ))

        valor_agua += v_agua
        valor_esgoto += v_esgoto
        restante -= m3_na_faixa
        piso = teto if teto is not None else piso

        if restante <= 0:
            break

    taxa_fixa = config.get("taxa_fixa_rs", 0.0)
    valor_total = valor_agua + valor_esgoto + taxa_fixa

    return WaterBill(
        consumo_m3=round(consumo_m3, 3),
        valor_agua=round(valor_agua, 2),
        valor_esgoto=round(valor_esgoto, 2),
        taxa_fixa=taxa_fixa,
        valor_total=round(valor_total, 2),
        faixas=faixas,
        configurado=config.get("configurado", False),
        categoria=config.get("categoria", ""),
    )
