# Яндекс Search API (xmlstock yandex/xml)

Эндпоинт: `https://xmlstock.com/yandex/xml/` — только XML-формат.

## Полный список GET-параметров

| Параметр | Обяз. | Описание |
|---|:-:|---|
| `user` | ✔ | ID пользователя в xmlstock |
| `key` | ✔ | API-ключ из ЛК |
| `query` | ✔ | Текст поискового запроса (≤ 40 слов / 400 символов) |
| `lr` | | Идентификатор региона ранжирования (Москва = 213, Питер = 2, и т.д.) |
| `l10n` | | Язык уведомлений в ответе: ru / uk / be / kk / tr / en (default `ru`) |
| `sortby` | | Сортировка результатов: `rlv` (релевантность, default) или `tm` (время изменения). Для `tm` можно указать порядок: `sortby=tm.order%3Dascending` или `descending` (default — descending) |
| `filter` | | `moderate` (default), `none`, `strict` (семейный) |
| `maxpassages` | | Кол-во пассажей сниппета: 1-5 (default до 4) |
| `groupby` | | Размер выдачи или сложная группировка по доменам (см. ниже) |
| `page` | | Номер страницы (0-based). **Hard cap: позиции > 250 → error 18** |
| `domain` | | Зона поиска Яндекса: `ru` / `by` (или `be`) / `kz` (или `kk`) / `com` / `com.tr` (или `tr`) / `uz`. Default `ru` |
| `device` | | `desktop` (default) / `mobile` / `tablet` / `iphone` / `android` |
| `noreask` | | `0` (исправлять опечатки, default) / `1` (не исправлять, точное соответствие) |
| `delayed` | | `1` — async режим, ответ — `req_id` (см. `async-and-req-id.md`) |
| `req_id` | | Получение результата по async-задаче (см. `async-and-req-id.md`) |

## Поисковые операторы в `query`

Можно комбинировать через пробел.

| Оператор | Пример | Эффект |
|---|---|---|
| `site:` | `site:https://example.com` | Поиск по конкретному домену (часто используется для подсчёта проиндексированных страниц) |
| `mime:` | `mime:pdf` | Тип файла: pdf, xls, ods, rtf, ppt, odp, swf, odt, odg, doc |
| `lang:` | `lang:en` | Язык документа: ru, en, de, fr |
| `date:` | `date:20240101` | Дата = указанная |
| `date:>` | `date:>20240101` | Поздее даты (`<`, `<=`, `>`, `>=`) |
| `date:..` | `date:20240101..20241231` | Диапазон |
| `date:` | `date:202401*` / `date:2024*` | Месяц / год с маской `*` |

Год обязателен; месяц/день могут быть `*`.

## `groupby` — два режима

### Плоский: количество результатов на страницу

```
&groupby=100
```

Допустимые значения: `10`, `20`, …, `100`. ТОП-100 в одном ответе.

### Продвинутый: группировка по доменам

Формат:

```
attr=<служебный_атрибут>.mode=<тип>.groups-on-page=<N>.docs-in-group=<M>
```

- `mode=flat` — каждая группа = 1 документ. `attr=` (пустое).
- `mode=deep` — каждая группа = документы одного домена. `attr=d`.
- `groups-on-page` — 1..100.
- `docs-in-group` — 1..3.

Пример (100 групп по 1 документу одного домена, классический ТОП-100 без повторов доменов):

```
&groupby=attr=d.mode=deep.groups-on-page=100.docs-in-group=1
```

## Списки регионов

- Часто используемые — в документации xmlstock в HTML-табличке "Список идентификаторов часто используемых стран и регионов Яндекса".
- Полный список — `csv` файл там же.
- Альтернатива: ввести регион в форме настроек ЛК — он покажет ID.

Самые ходовые: Москва `213`, СПб `2`, Россия `225`, Беларусь `149`, Казахстан `159`, Украина `187`.

## POST-режим (XML body)

Часть параметров остаётся в URL:
```
https://xmlstock.com/yandex/xml/?user=...&key=...&lr=213&domain=ru&device=desktop
```

Тело POST (Content-Type: `application/xml; charset=utf-8`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<request>
  <query>Окна</query>
  <sortby order="descending">tm</sortby>
  <maxpassages>2</maxpassages>
  <page>2</page>
  <groupings>
    <groupby attr="d" mode="deep" groups-on-page="10" docs-in-group="3" />
  </groupings>
</request>
```

**Важно**: в `query` амперсанды и спецсимволы должны быть XML-экранированы (`&amp;`, `&lt;`, `&gt;`, `&apos;`, `&quot;`). Невалидный XML → `error 18`.

## Hybrid режим — поведение по умолчанию

Без `delayed=1` ответ либо стандартный SERP, либо ошибка `210` ("запрос поставлен в очередь"). Retry — **тот же URL** через 20-30 секунд (запрос xmlstock запомнил, повторное списание **не** произойдёт). Списание было в момент первой отправки.

## Async режим

`&delayed=1` → ответ:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<yandexsearch version="2.0">
  <response date="20250204T185502">
    <req_id>spr3s0ngc4citnd30muk</req_id>
  </response>
</yandexsearch>
```

Получение результата:
```
https://xmlstock.com/yandex/xml/?user=...&key=...&req_id=spr3s0ngc4citnd30muk
```

Polling — не чаще раза в 20-30 с (см. `async-and-req-id.md`).

## Структура успешного ответа (XML)

Упрощённо:

```xml
<yandexsearch version="1.0">
  <response date="...">
    <reqid>...</reqid>
    <found priority="all">N</found>
    <found-docs priority="all">N</found-docs>
    <found-docs-human>...</found-docs-human>
    <results>
      <grouping attr="d" mode="deep" groups-on-page="..." docs-in-group="...">
        <found-docs priority="..."/>
        <page first="..." last="...">0</page>
        <group>
          <categ attr="d" name="example.com"/>
          <doccount>...</doccount>
          <relevance/>
          <doc id="...">
            <url>https://example.com/page</url>
            <domain>example.com</domain>
            <title>...</title>
            <headline>...</headline>
            <modtime>20240115T120000</modtime>
            <size>...</size>
            <charset>utf-8</charset>
            <passages>
              <passage>...текст с <hlword>ключом</hlword>...</passage>
            </passages>
            <mime-type>text/html</mime-type>
            <saved-copy-url>...</saved-copy-url>
          </doc>
        </group>
      </grouping>
    </results>
  </response>
</yandexsearch>
```

## Особые кейсы

### Проверка количества проиндексированных страниц сайта

```
&query=site:https://example.com&groupby=attr=d.mode=deep.groups-on-page=100.docs-in-group=1
```

В элементе `<found-docs priority="all">` — общее число. Это **оценка** Яндекса, не точное число.

### Проверка позиции сайта по фразе

Запросить ТОП-100 (`groupby=100` или с группировкой по домену) для нужного `lr` / `domain` / `device`, найти первое вхождение целевого домена в `<doc><domain>`. Позиция = индекс группы + 1 (учитывая `groups-on-page` × `page`).

### Мобильная выдача

`&device=mobile`. Принципиально может отличаться от десктопной по составу и порядку.
