# References

Rule (AGENTS.md): every entry has a DOI, arXiv ID or manufacturer URL, and a "verified"
line saying when, by whom and how. "Metadata verified" means the identifier resolves
and title, authors, journal, volume and pages match. "Content verified" means the
cited claim was read on the page itself. A number may be quoted from a reference only
after content verification of that number.

## Scintillator photonic crystals

**[Knapitsch2012]** A. Knapitsch, E. Auffray, C. W. Fabjan, J.-L. Leclercq, X. Letartre,
R. Mazurczyk, P. Lecoq, "Results of Photonic Crystal Enhanced Light Extraction on Heavy
Inorganic Scintillators," *IEEE Trans. Nucl. Sci.* **59**(5), 2334–2339 (2012).
doi:10.1109/TNS.2012.2184556
- Metadata verified 2026-10-15 (Claude; DOI resolution, CERN Crystal Clear and TU Wien
  repository listings).
- Content verified: not yet. The brief's "30–60 % light-yield gain" is not quoted
  anywhere in this repo until someone reads it on the paper.

**[CarrDelgado2024]** H. Carr Delgado, P. Moradifar, G. Chinn, C. S. Levin, J. A. Dionne,
"Toward 'super-scintillation' with nanomaterials and nanophotonics," *Nanophotonics*
**13**(12) (2024). doi:10.1515/nanoph-2023-0946
- Metadata verified 2026-10-15 (Claude; DOI and PMC listing PMC11090085; published
  2024-04-15).
- Content verified: not yet.

## Methods

**[Kim2023]** C. Kim, B. Lee, "TORCWA: GPU-accelerated Fourier modal method and
gradient-based optimization for metasurface design," *Comput. Phys. Commun.* **282**,
108552 (2023). doi:10.1016/j.cpc.2022.108552
Code: https://github.com/kch3782/torcwa (PyPI `torcwa` 0.1.4.2 used here; LGPL).
- Metadata verified 2026-10-15 (Claude; GitHub README and two independent web listings
  agree on journal, volume, article number and DOI).
- Conventions used from the code itself (read in the installed package, not the paper):
  `exp(-jωt)`, lengths in the unit of 1/freq, incident angle defined in the input layer.

**[BornWolf]** M. Born, E. Wolf, *Principles of Optics*, 7th ed., Cambridge University
Press (1999), §1.5 (Fresnel formulae) and §1.5.4 (total reflection).
- Standard textbook; sign convention for r_p as stated in AGENTS.md. Any edition
  Aziz has access to is acceptable; page numbers to be added by Aziz.

## Material constants (PROVISIONAL until Aziz confirms; see docs/decisions.md)

**[Luxium-LYSO]** Luxium Solutions, "LYSO Scintillation Crystal" product page,
https://luxiumsolutions.com/radiation-detection-scintillators/crystal-scintillators/lyso-scintillation-crystals
- Content verified 2026-10-15 (Claude, via page fetch): "Wavelength of emission max
  [nm]: 420"; "Refractive index @ emission max: 1.81"; decay time 36 ns; density
  7.1 g/cm³; light yield 33 200 photons/MeV (typical, 1 cm³). The page also links a
  "Luxium-LYSO-Material-Data-Sheet" PDF (not fetched).

**[Luxium-BGO]** Luxium Solutions, "BGO Scintillation Material" product page,
https://luxiumsolutions.com/radiation-detection-scintillators/crystal-scintillators/bgo-bismuth-germanate
- Content verified 2026-10-15 (Claude, via page fetch): "Wavelength of emission max.
  [nm]: 480"; "Refractive index @ emission max: 2.15"; primary decay time 300 ns;
  density 7.13 g/cm³; light yield 8–10 photons/keV.

**[Epic-LYSO]** Epic Crystal Co., Ltd., "LYSO(Ce) Crystal" product page,
https://www.epic-crystal.com/scintillation-crystals/lysoce-crystal.html
- Content verified 2026-10-15 (Claude, via page fetch): emission peak 420 nm,
  refractive index 1.82 (wavelength not stated), decay 40 ns, density 7.25 g/cm³,
  light output 30 000 ph/MeV. Second source only; shows the vendor spread in n.

**[Epic-BGO]** Epic Crystal Co., Ltd., "BGO Crystal" product page,
https://www.epic-crystal.com/scintillation-crystals/bgo-crystal.html
- Content verified 2026-10-15 (Claude, via page fetch): emission peak 480 nm,
  refractive index 2.15, decay 317 ns, density 7.13 g/cm³, light output 8 500 ph/MeV.

**Optical grease n ≈ 1.5**: working value from the brief; no datasheet chosen yet.
To be cited before M3 (candidate: a silicone optical-coupling compound datasheet).
