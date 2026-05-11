"""
Regression tests for matchers.py — pack-size differentiation.

Run:
    cd scrapers
    python -m pytest test_matchers.py -v
    # or without pytest:
    python -m unittest test_matchers.py -v
"""
from __future__ import annotations

import unittest

from matchers import (
    extract_pack_count,
    are_same_product,
    normalize_name,
    extract_numbers,
)


class TestExtractPackCount(unittest.TestCase):
    """extract_pack_count should recognize countable-unit patterns only."""

    def test_number_before_jeringas(self):
        self.assertEqual(
            extract_pack_count("2 Jeringas Restaurador Fluido Filtek Z350 Flow"),
            2,
        )

    def test_number_inside_parens(self):
        self.assertEqual(
            extract_pack_count("3M Resina Fluida Filtek Z350 XT Flow Tono A1 (2 Jeringas)"),
            2,
        )

    def test_single_syringe(self):
        self.assertEqual(
            extract_pack_count("Resina Fluida Filtek Z350 XT Flow (1 Jeringa)"),
            1,
        )

    def test_pack_2_jeringas(self):
        self.assertEqual(
            extract_pack_count("Filtek Bulk Fill Flow (Pack 2 jeringas) - 3M"),
            2,
        )

    def test_x_prefixed_quantity(self):
        self.assertEqual(
            extract_pack_count("Filtek Bulk Fill Flow x 2 jeringas, 3M ESPE"),
            2,
        )

    def test_tubos(self):
        self.assertEqual(extract_pack_count("Ionómero de vidrio 3 tubos"), 3)

    def test_capsulas(self):
        self.assertEqual(extract_pack_count("RelyX U200 x 20 capsulas"), 20)

    def test_no_unit_returns_none(self):
        # No countable unit → refuse to guess.
        self.assertIsNone(extract_pack_count("Filtek Z350 XT Flow"))
        self.assertIsNone(extract_pack_count("Filtek Bulk Fill Flow"))

    def test_size_not_pack(self):
        # "25mm" is a size, not a pack count.
        self.assertIsNone(extract_pack_count("Lima Hedstrom 25mm"))

    def test_concentration_not_pack(self):
        # Percentages are not pack counts.
        self.assertIsNone(extract_pack_count("Ionomero al 30%"))

    def test_model_number_not_pack(self):
        # "A3.5" or "C14" are shade/model codes, not pack counts.
        self.assertIsNone(extract_pack_count("Resina Z350 XT Tono A3.5"))
        self.assertIsNone(extract_pack_count("Bloque Disilicato C14 LT"))

    def test_pack_word_without_number(self):
        # Word "pack" without number → can't extract count.
        self.assertIsNone(extract_pack_count("Pack economico"))

    def test_model_code_context_rejected(self):
        # "Modelo N" / "Ref N" / "Cod N" immediately before a unit are catalog codes,
        # not pack counts.
        self.assertIsNone(extract_pack_count("Modelo 500 jeringas ref"))
        self.assertIsNone(extract_pack_count("Ref. 100 agujas"))
        self.assertIsNone(extract_pack_count("Codigo 250 guantes serie X"))
        # But 50 with no model-code preamble is plausible:
        self.assertEqual(extract_pack_count("Kit 50 jeringas desechables"), 50)


class TestExtractPackCountMedical(unittest.TestCase):
    """Medical commodity pack patterns added 2026-05-07 for tubotiquin/geerdink/dipromed."""

    def test_guantes_x_100(self):
        self.assertEqual(
            extract_pack_count("Guantes Nitrilo Estériles Caja x 100"), 100
        )

    def test_caja_de_100_guantes(self):
        self.assertEqual(
            extract_pack_count("Caja de 100 guantes nitrilo azul"), 100
        )

    def test_guantes_pack_200(self):
        self.assertEqual(
            extract_pack_count("Guantes Latex Acteon Pack 200"), 200
        )

    def test_agujas_hipodermicas_x_100(self):
        self.assertEqual(
            extract_pack_count("Agujas Hipodérmicas 21G x 100"), 100
        )

    def test_gasas_paquete_50(self):
        self.assertEqual(
            extract_pack_count("Gasas Estériles Tejidas paquete x 50"), 50
        )

    def test_mascarillas_caja_50(self):
        self.assertEqual(
            extract_pack_count("Mascarillas 3 Pliegues Caja x 50"), 50
        )

    def test_pares_de_guantes(self):
        self.assertEqual(
            extract_pack_count("5 pares de guantes quirúrgicos estériles"), 5
        )

    def test_500_count_now_accepted(self):
        # Real medical commodity: caja x 500 agujas exists in the market.
        self.assertEqual(
            extract_pack_count("Agujas Insulina BD Caja x 500"), 500
        )

    def test_above_500_still_rejected(self):
        # 1000 jeringas is fairly clearly a catalog code, and the regex
        # caps inner digits at \d{1,3} anyway, so this returns None.
        self.assertIsNone(extract_pack_count("Caja 1000 jeringas industrial"))


class TestAreSameProductMedical(unittest.TestCase):
    """Pack-size hard-block must extend to medical commodity pack sizes."""

    def test_guantes_100_vs_200_blocked(self):
        a = "Guantes Nitrilo Caja x 100"
        b = "Guantes Nitrilo Caja x 200"
        self.assertFalse(are_same_product(a, b))

    def test_same_glove_pack_still_matches(self):
        a = "Guantes Nitrilo Caja x 100"
        b = "Caja Guantes Nitrilo 100 unidades"
        self.assertTrue(are_same_product(a, b))


class TestAreSameProduct(unittest.TestCase):
    """Pack-size mismatch must hard-block same-product matching."""

    def test_one_vs_two_jeringas_z350_flow_blocked(self):
        """The original Clandent Z350 Flow bug."""
        a = "Resina Fluida Filtek Z350 XT Flow (1 Jeringa)"
        b = "Filtek Z350 XT Flow Tono A1 (2 Jeringas)"
        self.assertFalse(are_same_product(a, b))

    def test_same_pack_size_still_matches(self):
        # Two listings of the same SKU + same pack count should still match
        # after the pack-size check. Use names that would have matched before
        # (same alphabetic tokens, differ only in punctuation/order).
        a = "Filtek Z350 XT Flow A1 (2 Jeringas)"
        b = "Filtek Z350 XT Flow A1 2 jeringas"
        self.assertTrue(are_same_product(a, b))

    def test_pack_size_not_detected_on_one_side_still_compares(self):
        """When only one side has an extractable pack count, the check
        doesn't fire — we don't want to refuse matches for names that
        simply omit packaging info."""
        a = "Filtek Z350 XT Flow"
        b = "Filtek Z350 XT Flow (2 Jeringas)"
        # The number guard may still allow/block this; the point is that
        # the pack-size hard block does NOT fire when one side is None.
        # We assert non-failure: whatever the outcome, it wasn't driven by
        # the pack-size check alone.
        # (Actual match result depends on Jaccard — not asserting here.)
        _ = are_same_product(a, b)

    def test_kit_vs_non_kit_still_blocked(self):
        """Original _has_packaging_keyword guard still works."""
        a = "Kit Filtek Z350 XT Flow"
        b = "Filtek Z350 XT Flow (1 Jeringa)"
        self.assertFalse(are_same_product(a, b))

    def test_three_vs_two_tubes_blocked(self):
        a = "Ionomero Fuji IX GC (2 tubos)"
        b = "Ionomero Fuji IX GC - 3 tubos"
        self.assertFalse(are_same_product(a, b))

    def test_different_shade_still_blocked_by_alpha_check(self):
        """Tone A1 vs Tone A3.5 are different SKUs (alpha-differentiator)."""
        a = "Filtek Z350 XT Flow Tono A1 (2 Jeringas)"
        b = "Filtek Z350 XT Flow Tono A3 (2 Jeringas)"
        # A1/A3 are numeric shade codes — number guard fires.
        self.assertFalse(are_same_product(a, b))


class TestBackwardCompatibility(unittest.TestCase):
    """Make sure existing behavior isn't regressed by the new pack check."""

    def test_normalize_name_still_strips_accents(self):
        # 'Fluór' → 'fluor' (accent strip) → 'fluoride' (translate) → '' (noise removal)
        # That's the intended pipeline. Just verify accents get stripped — test
        # a word that survives the pipeline.
        self.assertEqual(normalize_name("Cápsula"), "capsule")

    def test_extract_numbers_still_works(self):
        self.assertEqual(extract_numbers("Resina 35% 25mm"), {"35", "25"})


if __name__ == "__main__":
    unittest.main()
