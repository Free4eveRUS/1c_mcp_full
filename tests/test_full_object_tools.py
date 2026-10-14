from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BSL = ROOT / "src/1c_ext/DataProcessors/mcp_ИнструментДанные1С/Ext/ManagerModule.bsl"
IDEMPOTENT_BSL = ROOT / "src/1c_ext/DataProcessors/mcp_ИнструментИдемпотентныеОперации/Ext/ManagerModule.bsl"
IDEMPOTENT_META = ROOT / "src/1c_ext/DataProcessors/mcp_ИнструментИдемпотентныеОперации.xml"
EXECUTION = ROOT / "src/1c_ext/CommonModules/mcp_Выполнение/Ext/Module.bsl"
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

IDEMPOTENT_TOOLS = {
    "onec_idempotent_write_object",
    "onec_idempotent_create_on_basis",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def function_body(text: str, name: str) -> str:
    marker = f"Функция {name}("
    start = text.index(marker)
    end = text.index("КонецФункции", start)
    return text[start:end]


def test_metadata_xml_is_well_formed():
    for path in [CONFIG, SUBSYSTEM, ROLE, RIGHTS, IDEMPOTENT_META]:
        ET.parse(path)


def test_all_tools_are_registered_and_dispatched():
    text = read(BSL)
    for tool in TOOLS:
        assert text.count(f'"{tool}"') >= 2, tool


def test_idempotent_tools_are_registered_and_dispatched():
    text = read(IDEMPOTENT_BSL)
    for tool in IDEMPOTENT_TOOLS:
        assert text.count(f'"{tool}"') >= 2, tool
    assert 'ПараметрИнструмента("idempotencyKey"' in text


def test_container_is_registered_in_configuration_and_subsystem():
    config = read(CONFIG)
    subsystem = read(SUBSYSTEM)
    rights = read(RIGHTS)
    assert "<DataProcessor>mcp_ИнструментДанные1С</DataProcessor>" in config
    assert "<DataProcessor>mcp_ИнструментИдемпотентныеОперации</DataProcessor>" in config
    assert "<Role>mcp_ИнструментДанные1С</Role>" in config
    assert "DataProcessor.mcp_ИнструментДанные1С" in subsystem
    assert "DataProcessor.mcp_ИнструментИдемпотентныеОперации" in subsystem
    assert "DataProcessor.mcp_ИнструментИдемпотентныеОперации" in rights


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
    idempotent = read(IDEMPOTENT_BSL)
    assert re.search(r"Документ\.Заполнить\(Основание\)", idempotent)


def test_idempotent_creation_assigns_command_uuid_before_write():
    text = read(IDEMPOTENT_BSL)
    assert "ПроверитьКлючИдемпотентности" in text
    assert "ПолучитьСсылку(МетаТип, Имя, КлючИдемпотентности)" in text
    assert "ПолучитьСсылку(\"Documents\", Аргументы.targetDocument, КлючИдемпотентности)" in text
    assert text.count("УстановитьСсылкуНового") >= 3
    assert text.count("СсылкаСуществует") >= 4


def test_idempotent_replay_returns_existing_object_before_creation():
    text = read(IDEMPOTENT_BSL)
    write_body = function_body(text, "ИдемпотентноЗаписатьОбъект")
    basis_body = function_body(text, "ИдемпотентноСоздатьНаОсновании")

    write_guard = write_body.index(
        "Если СсылкаСуществует(МетаТип, Имя, СсылкаИдемпотентности) Тогда"
    )
    catalog_create = write_body.index("Объект = Справочники[Имя].СоздатьЭлемент()")
    document_create = write_body.index("Объект = Документы[Имя].СоздатьДокумент()")
    assert write_guard < catalog_create
    assert write_guard < document_create
    assert "СсылкаИдемпотентности.ПолучитьОбъект()" in write_body

    basis_guard = basis_body.index(
        'Если СсылкаСуществует("Documents", Аргументы.targetDocument, СсылкаНового) Тогда'
    )
    basis_create = basis_body.index(
        "Документ = Документы[Аргументы.targetDocument].СоздатьДокумент()"
    )
    assert basis_guard < basis_create
    assert "СсылкаНового.ПолучитьОбъект()" in basis_body


def test_deterministic_link_is_assigned_before_first_write():
    text = read(IDEMPOTENT_BSL)
    write_body = function_body(text, "ИдемпотентноЗаписатьОбъект")
    basis_body = function_body(text, "ИдемпотентноСоздатьНаОсновании")

    first_write_link = write_body.index("Объект.УстановитьСсылкуНового")
    first_write = write_body.index("Объект.Записать()")
    assert first_write_link < first_write

    basis_link = basis_body.index("Документ.УстановитьСсылкуНового(СсылкаНового)")
    basis_write = basis_body.index("ЗаписатьДокументВРежиме(Документ")
    assert basis_link < basis_write


def test_batch_has_transaction_and_rollback():
    text = read(BSL)
    assert "НачатьТранзакцию()" in text
    assert "ЗафиксироватьТранзакцию()" in text
    assert "ОтменитьТранзакцию()" in text
    assert "Вложенный onec_batch запрещен" in text


def test_full_tool_results_cross_mcp_boundary_as_json_text():
    text = read(EXECUTION)
    assert 'ИмяОбработки = "mcp_ИнструментДанные1С"' in text
    assert 'ИмяОбработки = "mcp_ИнструментИдемпотентныеОперации"' in text
    assert "mcp_ОбщегоНазначения.ЗначениеВJSON(РезультатВыполнения)" in text
    assert "mcp_Содержимое.ТекстовоеСодержимое(JSONРезультат)" in text


def test_no_dynamic_bsl_execution_primitive_added():
    for path in [BSL, IDEMPOTENT_BSL]:
        text = read(path)
        # Запрос.Выполнить() is a normal query method and must remain allowed.
        # Block only standalone dynamic-language execution primitives.
        assert not re.search(r"(?mi)^\s*Выполнить\s*\(", text)
        assert not re.search(r"(?mi)(?<!\.)\bВычислить\s*\(", text)
