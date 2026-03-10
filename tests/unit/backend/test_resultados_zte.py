import pytest

from src.backend.mixins.common_mixin import CommonMixin
from tests.helpers.helpers_construccion import get_path_strict, path_exists

CASES_ZTE_BASE = [
    
]

CASES_ZTE = None
@pytest.mark.parametrize("name, modo, add_tests, remove_tests, expect", CASES_ZTE)
def test_resultados_zte_por_modo(name, modo, add_tests, remove_tests, expect,
                                 zte_base_payload, opts_por_modo, payload_builder, dummy_factory):
    payload = payload_builder(
        zte_base_payload,
        add_tests = add_tests,
        remove_tests = remove_tests,
    )

    opts = opts_por_modo[modo]

    dummy = dummy_factory(payload, opts)
    out = CommonMixin._resultadosZTE(dummy)

    present = expect.get("present", {})
    missing = expect.get("missing", [])

    for path, expected in present.items():
        got = get_path_strict(out, path)
        assert got == expected, (name, path, got, expected, out)

    for path in missing:
        assert not path_exists(out, path), (name, path, out)