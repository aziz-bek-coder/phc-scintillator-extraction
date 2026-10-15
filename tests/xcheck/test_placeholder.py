"""Owner: Argon. Cross-check tests go here (AGENTS.md). This placeholder keeps the
directory in git and will be replaced by Argon's first PR."""

import phcscint.xcheck


def test_xcheck_package_exists() -> None:
    assert phcscint.xcheck.__doc__ is not None
