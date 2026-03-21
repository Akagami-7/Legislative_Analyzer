def test_translation_hindi():
    from src.compression.translator import translate_result, SUPPORTED_LANGUAGES
    from src.shared_schemas import AnalysisResult

    # Dummy result to translate
    dummy = AnalysisResult(
        bill_id="test",
        citizen_summary="This law protects your personal data.",
        key_changes=["Companies must get your consent before using your data."],
        affected_groups=["All Indian citizens"],
        rights_impact="Strengthens the right to privacy.",
        implementation_date="August 2023",
        tokens_input=1000,
        tokens_output=100,
        compression_ratio=0.9,
        carbon_saved_grams=5.0
    )

    result = translate_result(dummy, target_lang="hi")

    assert result["language"] == "Hindi"
    assert result["language_code"] == "hi"
    assert len(result["citizen_summary"]) > 0
    assert result["citizen_summary"] != dummy.citizen_summary  # must be different
    print(f"✅ Hindi: {result['citizen_summary']}")