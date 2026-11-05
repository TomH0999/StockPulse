"""Fiscalité simulée des comptes. Taux en vigueur au 01/01/2026 :
- prélèvements sociaux 18,6 % sur les revenus du capital (CSG relevée de 1,4 point, LFSS 2026, loi n° 2025-1403 du
  30/12/2025), flat tax (PFU) 31,4 % = 12,8 % d'impôt sur le revenu + 18,6 % ;
- assurance-vie exclue de la hausse : prélèvements sociaux 17,2 %.
Simulation indicative : vérifiez votre situation sur impots.gouv.fr (option barème, abattements, etc.)."""
from datetime import date

IR = 12.8
PS = 18.6
PS_AV = 17.2
PFU = round(IR + PS, 1)  # 31,4 %
SOURCE = "LFSS 2026 (loi n° 2025-1403 du 30/12/2025) : prélèvements sociaux 18,6 % (17,2 % en assurance-vie), PFU 31,4 %"
US_WITHHOLDING = 15.0  # retenue à la source américaine sur les dividendes avec le formulaire W-8BEN (convention France / États-Unis)
LOSS_CARRY_YEARS = 10


def _years_since(opened: str | None) -> float | None:
    if not opened:
        return None
    return (date.today() - date.fromisoformat(opened)).days / 365.25


def withdrawal(account_type: str, gain: float, opened: str | None) -> dict:
    """Impôt estimé si l'on retirait tout aujourd'hui."""
    gain = max(0.0, gain)
    years = _years_since(opened)
    if account_type in ("PEA", "PEA_PME", "PEA_JEUNE"):
        if years is None:
            return {"rate": None, "tax": None, "note": "pea_no_date"}
        rate = PS if years >= 5 else round(IR + PS, 1)
        return {"rate": rate, "tax": round(gain * rate / 100, 2), "note": "pea_mature" if years >= 5 else "pea_before_5y"}
    if account_type == "AV":
        rate = PS_AV + (7.5 if years is not None and years >= 8 else IR)
        return {"rate": rate, "tax": round(gain * rate / 100, 2), "note": "av_after_8y" if years is not None and years >= 8 else "av_before_8y"}
    return {"rate": PFU, "tax": round(gain * PFU / 100, 2), "note": "cto_pfu"}


def cto_year(realized_by_year: dict[int, float], dividends_by_year: dict[int, float], year: int | None = None) -> dict:
    """Compte-titres : plus-values nettes de l'année après imputation des moins-values des 10 années précédentes,
    dividendes imposés au PFU, et moins-values encore reportables (avec leur année d'expiration)."""
    year = year or date.today().year
    carry: list[list] = []  # [année, montant restant]
    taxable_by_year = {}
    for y in sorted(set(realized_by_year) | {year}):
        if y > year:
            break
        carry = [c for c in carry if y - c[0] <= LOSS_CARRY_YEARS]
        net = realized_by_year.get(y, 0.0)
        if net < 0:
            carry.append([y, -net])
            taxable = 0.0
        else:
            for c in carry:
                used = min(c[1], net)
                c[1] -= used
                net -= used
            carry = [c for c in carry if c[1] > 0.005]
            taxable = net
        taxable_by_year[y] = taxable
    gains = taxable_by_year.get(year, 0.0)
    divs = dividends_by_year.get(year, 0.0)
    return {"year": year, "taxable_gains": round(gains, 2), "dividends": round(divs, 2),
            "tax": round((gains + divs) * PFU / 100, 2), "rate": PFU,
            "losses_carried": [{"year": y, "amount": round(a, 2), "expires": y + LOSS_CARRY_YEARS} for y, a in carry]}


def rates() -> dict:
    return {"ir": IR, "ps": PS, "ps_av": PS_AV, "pfu": PFU, "us_withholding": US_WITHHOLDING, "source": SOURCE}
