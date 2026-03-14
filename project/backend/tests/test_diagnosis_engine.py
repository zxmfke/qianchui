"""DiagnosisEngine 3层7维诊断引擎的纯单元测试（不依赖 API/DB）"""

import pytest

from app.services.diagnosis_engine import DiagnosisEngine


class TestDiagnosisEngineParsing:
    def test_parse_basic_conversation(self):
        engine = DiagnosisEngine()
        text = "客服：你好\n客户：我想了解双眼皮"
        result = engine.diagnose(text)
        assert "classification" in result
        assert "score_result" in result

    def test_parse_empty_text(self):
        engine = DiagnosisEngine()
        result = engine.diagnose("")
        assert "error" in result

    def test_parse_no_valid_turns(self):
        engine = DiagnosisEngine()
        result = engine.diagnose("这是一段普通文本\n没有对话格式")
        assert "error" in result


class TestDiagnosisEngineClassification:
    def test_ultra_short_dialog_skip(self):
        engine = DiagnosisEngine()
        text = "客服：你好"
        result = engine.diagnose(text)
        assert result.get("skip_reason") is not None

    def test_short_dialog(self):
        engine = DiagnosisEngine()
        text = "客服：你好\n客户：你好\n客服：请问有什么可以帮您"
        result = engine.diagnose(text)
        assert result["classification"]["dialog_depth"] == "short"

    def test_normal_dialog(self):
        engine = DiagnosisEngine()
        text = (
            "客服：你好\n客户：我想了解双眼皮\n"
            "客服：好的，双眼皮有全切和埋线\n客户：价格呢\n"
            "客服：全切大概在5000-8000\n客户：恢复期多久"
        )
        result = engine.diagnose(text)
        assert result["classification"]["dialog_depth"] == "normal"


class TestDiagnosisEngineScoring:
    def _good_conversation(self):
        return """客服：您好，很高兴为您服务，请问您想了解哪方面的项目呢？
客户：我想了解下双眼皮
客服：好的，您之前了解过双眼皮吗？双眼皮主要有埋线和全切两种方式，各有优势。我可以帮您分析一下哪种更适合您。
客户：没有了解过，能详细说说吗
客服：当然可以。埋线双眼皮恢复快，适合眼皮薄的人；全切效果更持久，适合眼皮松弛的情况。我理解您可能比较关心恢复期和效果，这些都是正常的担忧。
客户：恢复期大概多久呢
客服：埋线大概3-5天消肿，全切需要1-2周。不用担心，我们的医生经验非常丰富，会根据您的眼型设计最适合的方案。方便的话，我帮您预约一个免费面诊，医生可以面对面帮您分析。
客户：好的，可以预约"""

    def _bad_conversation(self):
        return """客服：方便留个电话吗
客户：什么项目都没说呢
客服：还在吗
客服：能收到消息吗
客服：请问还在吗
客服：我们医院双眼皮做得很好
客服：留个电话吧
客服：电话留下方便联系
客户：别发了"""

    def test_good_conversation_high_score(self):
        engine = DiagnosisEngine()
        result = engine.diagnose(self._good_conversation())
        assert result["score_result"]["overall"] >= 60

    def test_bad_conversation_low_score(self):
        engine = DiagnosisEngine()
        result = engine.diagnose(self._bad_conversation())
        assert result["score_result"]["overall"] < 60

    def test_scoring_dimensions(self):
        engine = DiagnosisEngine()
        result = engine.diagnose(self._good_conversation())
        dims = result["score_result"]["dimensions"]
        assert "A1_rhythm" in dims
        assert "A2_value_progression" in dims
        assert "B1_first_reply" in dims
        assert "C1_engagement" in dims
        assert "C2_warmth" in dims
        for dim_data in dims.values():
            assert "score" in dim_data
            assert "weight" in dim_data

    def test_grade_mapping(self):
        engine = DiagnosisEngine()
        assert engine._grade(90) == "A"
        assert engine._grade(75) == "B"
        assert engine._grade(60) == "C"
        assert engine._grade(40) == "D"


class TestDiagnosisEngineRootCause:
    def test_root_causes_identified(self):
        engine = DiagnosisEngine()
        text = """客服：方便留个电话吗
客户：你好
客服：留个电话吧
客服：还在吗
客服：请问还在吗
客服：能收到消息吗
客户：不需要"""
        result = engine.diagnose(text)
        assert len(result["root_causes"]) > 0
        cause_types = [c["type"] for c in result["root_causes"]]
        assert any(t in cause_types for t in ["config", "script", "traffic"])

    def test_search_term_detection(self):
        engine = DiagnosisEngine()
        text = "客服：你好\n客户：我想问下双眼皮\n客服：好的，双眼皮项目很受欢迎"
        result = engine.diagnose(text, search_term="双眼皮")
        b1 = result["score_result"]["dimensions"]["B1_first_reply"]
        assert any("搜索词" in d for d in b1["details"]) or b1["score"] >= 70


class TestDiagnosisEngineCustomWeights:
    def test_custom_industry_weights(self):
        weights = {"A1": 30, "A2": 10, "B1": 10, "B2": 10, "B3": 10, "C1": 20, "C2": 10}
        engine = DiagnosisEngine(industry_weights=weights)
        text = "客服：你好\n客户：了解双眼皮\n客服：好的\n客户：价格呢\n客服：5000起"
        result = engine.diagnose(text)
        assert result["score_result"]["dimensions"]["A1_rhythm"]["weight"] == 30
        assert result["score_result"]["dimensions"]["C1_engagement"]["weight"] == 20
