"""Material constants (owner: Claude).

Every value points at an entry in docs/references.md. Values are PROVISIONAL until
Aziz confirms them (docs/decisions.md, 2026-10-15): they come from manufacturer
product pages that were fetched and read, but Aziz has not yet opened them himself.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scintillator:
    name: str
    n: float  # refractive index at the emission peak
    wavelength_um: float  # emission peak, micrometres
    reference: str  # key in docs/references.md
    status: str = "PROVISIONAL"


LYSO = Scintillator(name="LYSO:Ce", n=1.81, wavelength_um=0.420, reference="Luxium-LYSO")
BGO = Scintillator(name="BGO", n=2.15, wavelength_um=0.480, reference="Luxium-BGO")

# Second-vendor value for LYSO, kept to quantify the vendor spread (Epic-LYSO).
LYSO_N_EPIC = 1.82

N_AIR = 1.0
# Optical coupling grease: Eljen EJ-550 datasheet value (docs/references.md, Eljen-EJ550);
# wavelength not stated by the manufacturer, assumed valid at the emission peak.
# Luxium BC-631 lists 1.465. PROVISIONAL.
N_GREASE = 1.46
# The project brief's round value, kept only to reproduce the brief's 21.7 % check.
N_GREASE_BRIEF = 1.5


def n_si3n4_luke(wavelength_um: float) -> float:
    """Si3N4 refractive index, Sellmeier fit of Luke et al., Opt. Lett. 40, 4823 (2015),
    doi:10.1364/OL.40.004823, as tabulated by refractiveindex.info (docs/references.md):
    n^2 - 1 = 3.0249 l^2/(l^2 - 0.1353406^2) + 40314 l^2/(l^2 - 1239.842^2), l in um,
    valid 0.310 to 5.504 um. Real index only (the record has no k). PROVISIONAL."""
    lam = float(wavelength_um)
    if not 0.310 <= lam <= 5.504:
        raise ValueError("outside the validity range of the Luke 2015 fit")
    l2 = lam * lam
    n2 = 1 + 3.0249 * l2 / (l2 - 0.1353406**2) + 40314 * l2 / (l2 - 1239.842**2)
    return n2**0.5
