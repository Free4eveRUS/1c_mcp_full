from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BSL = ROOT / "src/1c_ext/DataProcessors/mcp_ИнструментДанные1С/Ext/ManagerModule.bsl"
CONFIG = ROOT / "src/1c_ext/Configuration.xml"
SUBSYSTEM = ROOT / "src/1c_ext/Subsystems/mcp_MCPСервер/Subsystems/mcp_КонтейнерыИнструментов.xml"
ROLE = ROOT / "src/1c_ext/Roles/mcp_ИнструментДанные1С.xml"
RIGHTS = ROOT / "src/1c_ext/Roles/mcp_ИнструментДанные1С/Ext/Rights.xml"

TOOLS = {
    "onec_find_objects",
    "onec_read_object",
    "onec_write_object",
    "onec_delete_mark",
    "onec_post_document",
    "onec_unpost_document",
    "onec_create_on_basis",
    "onec_fill_on_basis",
    "onec_execute_query",
    "onec_get_document_movements",
    "onec_read_register",
    "onec_batch",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_metadata_xml_is_well_formed():
    for path in [CONFIG, SUBSYSTEM, ROLE, RIGHTS]:
        ET.parse(path)


def test_all_tools_are_registered_and_dispatched():
    text = read(BSL)
    for tool in TOOLS:
        assert text.count(f'"{tool}"') >= 2, tool


def test_container_is_registered_in_configuration_and_subsystem():
    config = read(CONFIG)
    subsystem = read(SUBSYSTEM)
    assert "<DataProcessor>mcp_ИнструментДанные1С</DataProcessor>" in config
    assert "<Role>mcp_ИнструментДанные1С</Role>" in config
    assert "DataProcessor.mcp_ИнструментДанные1С" in subsystem


def test_posted_document_direct_save_is_guarded():
    text = read(BSL)
    assert "Проведенный документ нельзя менять обычной записью" in text
    assert "onec_batch: unpost -> write -> post" in text


def test_query_tool_is_read_only_guarded():
    text = read(BSL)
    assert 'Лев(ВРег(Текст), 7) <> "ВЫБРАТЬ"' in text
    assert "Разрешены только запросы, начинающиеся с ВЫБРАТЬ" in text


def test_create_on_basis_uses_platform_fill():
    text = read(BSL)
    assert re.search(r"Документ\.Заполнить\(Основание\)", text)


def test_batch_has_transaction_and_rollback():
    text = read(BSL)
    assert "НачатьТранзакцию()" in text
    assert "ЗафиксироватьТранзакцию()" in text
    assert "ОтменитьТранзакцию()" in text
    assert "Вложенный onec_batch запрещен" in text


def test_no_dynamic_bsl_execution_primitive_added():
    text = read(BSL)
    forbidden = ["Выполнить(", "Вычислить("]
    for token in forbidden:
        assert token not in text, token
