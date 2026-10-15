# References

Rule (AGENTS.md): every entry has a DOI or arXiv ID, and a "verified" line saying when
and where it was checked. "Metadata verified" means the DOI resolves and the title,
authors, journal, volume and pages match; "content verified" means Aziz opened the
paper and read the cited claim. A reference may be cited in a doc only after content
verification.

## Scintillator photonic crystals

**[Knapitsch2012]** A. Knapitsch, E. Auffray, C. W. Fabjan, J.-L. Leclercq, X. Letartre,
R. Mazurczyk, P. Lecoq, "Results of Photonic Crystal Enhanced Light Extraction on Heavy
Inorganic Scintillators," *IEEE Trans. Nucl. Sci.* **59**(5), 2334–2339 (2012).
doi:10.1109/TNS.2012.2184556
- Metadata verified 2026-10-15 (Claude, via DOI resolution and CERN/TU Wien listings).
- Content verified: **not yet** (Aziz to open and record the measured light-yield gain
  before any number from it is quoted in the docs; the brief's "30–60 %" stays unquoted
  until then).

**[CarrDelgado2024]** H. Carr Delgado, P. Moradifar, G. Chinn, C. S. Levin, J. A. Dionne,
"Toward 'super-scintillation' with nanomaterials and nanophotonics," *Nanophotonics*
(2024). doi:10.1515/nanoph-2023-0946
- Metadata verified 2026-10-15 (Claude, via DOI and PMC listing PMC11090085).
- Content verified: not yet.

## Methods

**[Kim2023]** C. Kim, B. Lee, "TORCWA: GPU-accelerated Fourier modal method and
gradient-based optimization for metasurface design," *Comput. Phys. Commun.* **282**,
108552 (2023). doi:10.1016/j.cpc.2022.108552
Code: https://github.com/kch3782/torcwa (PyPI `torcwa`).
- Metadata verified 2026-10-15 (Claude, via GitHub README and Mendeley Data listing).
  The DOI above was taken from the package README and must be checked on the
  publisher page by Aziz before citing.

## Material constants (to be cited before M1 closes)

Working values used in the brief: LYSO n ≈ 1.82, emission peak ≈ 420 nm; BGO n ≈ 2.15,
emission peak ≈ 480 nm. Candidate sources found 2026-10-15, none yet content-verified:
- Berkeley Nucleonics LYSO datasheet (vendor page).
- CAEN educational note SG6115A, "A Comparison of Different Scintillating Crystals".
- Saint-Gobain / Luxium Solutions LYSO and BGO datasheets (preferred: manufacturer).
Action: Aziz picks one manufacturer datasheet per material, records the values and the
URL here, and `src/phcscint/materials.py` quotes this file.
