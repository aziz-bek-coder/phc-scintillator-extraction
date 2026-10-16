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
- Abstract content verified 2026-10-16 (Claude, via the TU Wien repositum record of
  the paper, handle 20.500.12708/163867; IEEE Xplore did not load): "Through the
  deposition of an auxiliary layer of silicon nitride", "introducing a photonic crystal
  (PhC) slab at the outcoupling surface of the scintillator", samples on
  "1.2 mm × 2.6 mm × 5 mm lutetium oxyorthosilicate (LSO) scintillators", and "we show a
  30-60% light yield improvement of the different PhC designs ... when compared to an
  unstructured reference scintillator". Lattice type, period, hole size, layer thickness
  and coupling medium are NOT in the abstract and have not been read (see
  docs/status.md).

**[Knapitsch2012thesis]** A. Knapitsch, "Photonic crystals: enhancing the light output
of scintillation based detectors", PhD thesis, Technische Universität Wien (2012),
handle 20.500.12708/8866, https://repositum.tuwien.at/handle/20.500.12708/8866
- Abstract read 2026-10-16 (Claude): PhC made "by using electron beam lithography and
  reactive ion etching (RIE)" on "1.2 x 2 x 5mm 3 LSO"; light simulated with "a
  Monte-Carlo program" and "a rigorous coupled wave analysis (RCWA) framework". Note the
  abstract's 2 mm differs from the IEEE abstract's 2.6 mm. The full-text PDF is
  copy-protected; its geometry chapter has not been read.

**[CarrDelgado2024]** H. Carr Delgado, P. Moradifar, G. Chinn, C. S. Levin, J. A. Dionne,
"Toward 'super-scintillation' with nanomaterials and nanophotonics," *Nanophotonics*
(2024), published 2024-04-15. doi:10.1515/nanoph-2023-0946 (volume and issue not yet
verified)
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

**[Macleod]** H. A. Macleod, *Thin-Film Optical Filters*, CRC Press (4th ed., 2010),
ch. 2 (characteristic matrix of a thin film).
- Standard textbook; used for derivation 03 eq. (10). Not content-checked by page;
  the formula is validated numerically against torcwa (`tests/test_rcwa_phc.py`) and
  against Fresnel at zero thickness.

**[Polyanskiy2024]** M. N. Polyanskiy, "Refractiveindex.info database of optical
constants", *Sci. Data* **11**, 94 (2024). doi:10.1038/s41597-023-02898-2
- The database's requested citation, listed on refractiveindex.info (read 2026-10-16).
  Cited together with the original data source whenever a value comes from the site.

## Pillar / layer materials

**[Luke2015]** K. Luke, Y. Okawachi, M. R. E. Lamont, A. L. Gaeta, M. Lipson,
"Broadband mid-infrared frequency comb generation in a Si3N4 microresonator",
*Opt. Lett.* **40**, 4823–4826 (2015). doi:10.1364/OL.40.004823
- Used via refractiveindex.info, page Si3N4 / Luke (read 2026-10-16 by Claude through
  the YAML record): formula 1 with coefficients 0, 3.0249, 0.1353406, 40314, 1239.842,
  valid 0.310–5.504 µm, n only. Sample: "340 nm Si3N4 on 3.1 μm of thermal SiO2 on
  silicon". The site's CSV values 2.0934554672447 at 0.4139 µm and 2.0731921339333 at
  0.4658 µm are reproduced by `materials.n_si3n4_luke` (tested).
- DOI resolves to Optica volume 40, issue 21, page 4823 (HTTP redirect checked); the
  publisher page was behind a bot check, so the title is from refractiveindex.info.

**[Philipp1973]** H. R. Philipp, "Optical properties of silicon nitride",
*J. Electrochem. Soc.* **120**, 295–300 (1973). doi:10.1149/1.2403440, with the
dispersion formula of T. Bååk, *Appl. Opt.* **21**, 1069–1072 (1982),
doi:10.1364/AO.21.001069 (via refractiveindex.info, Si3N4 / Philipp).
- Second Si3N4 source, used only to bound the index uncertainty: formula
  n² − 1 = 2.8939 λ²/(λ² − 0.13967²), valid 0.207–1.24 µm. Neither DOI opened yet.

TiO2 (not used, recorded for the choice in docs/decisions.md): refractiveindex.info
thin-film records disagree at 420 nm — Sarkar et al. 2019 (doi:10.1021/acsami.8b20535)
tabulates n = 2.294437, k = 0; Siefke et al. 2016 (doi:10.1002/adom.201600250, ALD
film) tabulates n ≈ 2.62 with k ≈ 1.3e-4 (interpolated between rows 0.41911801 µm and
0.421537605 µm).

## Coupling media

**[Eljen-EJ550]** Eljen Technology, "EJ-550, EJ-552 – Silicone Grease" product page,
https://eljentechnology.com/products/accessories/ej-550-ej-552
- Content verified 2026-10-16 (Claude, via page fetch): properties table
  "Refractive Index" 1.46 (EJ-550) and 1.47 (EJ-552). No wavelength or temperature
  stated. Used for `materials.N_GREASE` (PROVISIONAL).

**[Luxium-BC631]** Luxium Solutions, "Assembly Materials" page,
https://luxiumsolutions.com/radiation-detection-scintillators/assembly-materials
- Content verified 2026-10-16 (Claude): BC-631 silicone optical grease "has a specific
  gravity of 0.976 and 1.465 Index of Refraction". Corroborates EJ-550.

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

**Not found (searched 2026-10-16):** a dispersion formula n(λ) for LYSO/LSO (needed
for the group index) and an optical absorption length of LYSO at 420 nm. The likely
source, R. Mao, L. Zhang, R.-Y. Zhu, IEEE Trans. Nucl. Sci. 55(4), 2425 (2008),
doi:10.1109/TNS.2008.2000776, could not be opened (IEEE Xplore did not load); its
metadata is unverified. The Monte Carlo therefore uses n_g = n and treats absorption as
a scanned parameter (docs/decisions.md).
