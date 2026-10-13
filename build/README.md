# Build artifacts

`MCP_Сервер.cfe` в этой директории унаследован от upstream и соответствует исходному релизу **1.8.1**.

Исходники ветки `feature/full-object-tools` имеют версию **2.0.0** и содержат новый контейнер `mcp_ИнструментДанные1С`. До пересборки в 1С:Конфигураторе/Designer существующий `.cfe` **не содержит** новых `onec_*` tools.

Не используйте старый `.cfe` для проверки full-tools. Для теста загрузите исходники расширения из `src/1c_ext` в конфигуратор и пересоберите расширение, после чего замените `build/MCP_Сервер.cfe` полученным артефактом.

После пересборки проверить через `tools/list`, что доступны как минимум:

- `onec_create_on_basis`
- `onec_fill_on_basis`
- `onec_post_document`
- `onec_unpost_document`
- `onec_get_document_movements`
- `onec_execute_query`
- `onec_batch`
