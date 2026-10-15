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
N_GREASE = 1.5  # optical coupling grease, working value from the brief (no datasheet yet)
