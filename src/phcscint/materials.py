"""Material constants.

Every value here must point at an entry in docs/references.md. Values marked
PROVISIONAL are the working numbers from the project brief and are not yet
content-verified against a datasheet; do not quote them in any document.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scintillator:
    name: str
    n: float  # refractive index at the emission peak (PROVISIONAL until cited)
    wavelength_um: float  # emission peak, micrometres (PROVISIONAL until cited)
    reference: str  # key in docs/references.md


LYSO = Scintillator(name="LYSO:Ce", n=1.82, wavelength_um=0.420, reference="PROVISIONAL")
BGO = Scintillator(name="BGO", n=2.15, wavelength_um=0.480, reference="PROVISIONAL")

N_AIR = 1.0
N_GREASE = 1.5  # optical coupling grease, working value from the brief (PROVISIONAL)
