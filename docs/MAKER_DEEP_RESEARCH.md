# MAKER Deep Research - Руководство по использованию

## Обзор

MAKER Deep Research — это система глубокого исследования на основе методологии из научной статьи ["MAKER: Solving a Million-Step LLM Task with Zero Errors"](https://arxiv.org/abs/2511.09030).

### Ключевые принципы MAKER:
- **M**aximal Agentic decomposition — декомпозиция задач на атомарные под-задачи
- **K**-threshold voting — голосование с порогом k для верификации
- **E**rror mitigation — минимизация ошибок через консенсус
- **R**ed-flagging — отсев некачественных ответов

## Быстрый старт

### Базовое использование

```python
import asyncio
from maker.deep_research import DeepResearcher, WebSearchClient

async def main():
    # Создаём исследователя с дефолтными настройками
    researcher = DeepResearcher()

    # Запускаем исследование
    report = await researcher.research(
        question="Какие ключевые тренды в AI индустрии в 2024 году?",
        research_type="market"
    )

    # Выводим результаты
    print(report.synthesis)

asyncio.run(main())
```

### С интеграцией реального поиска

```python
import asyncio
from maker.deep_research import DeepResearcher, WebSearchClient

# Ваша функция поиска (интеграция с API)
async def my_search_function(query: str) -> list[dict]:
    """
    Возвращает результаты поиска в формате:
    [
        {
            "title": "Заголовок страницы",
            "url": "https://example.com/page",
            "snippet": "Краткое описание или выдержка из страницы...",
            "credibility": 0.85  # опционально, 0.0-1.0
        },
        ...
    ]
    """
    # Здесь ваша логика поиска
    # Например, интеграция с Google Search API, Bing, или др.
    results = await call_search_api(query)
    return results

async def main():
    # Создаём клиент поиска с вашей функцией
    search_client = WebSearchClient(search_fn=my_search_function)

    # Создаём исследователя
    researcher = DeepResearcher(
        search_client=search_client,
        voting_k=3,           # Порог голосования
        max_sub_queries=5     # Макс. количество под-запросов
    )

    # Запускаем исследование
    report = await researcher.research(
        question="Архитектура современных AI платформ",
        research_type="technical",
        verbose=True  # Показывать прогресс
    )

    print(report.synthesis)

asyncio.run(main())
```

## Типы исследований

Система поддерживает 4 типа исследований, каждый с оптимизированной декомпозицией:

### 1. `general` — Общее исследование
```python
report = await researcher.research(
    question="Что такое квантовые компьютеры?",
    research_type="general"
)
```
Генерирует под-запросы:
- Что это?
- Ключевые компоненты
- Последние разработки
- Основные проблемы
- Мнения экспертов

### 2. `technical` — Техническое исследование
```python
report = await researcher.research(
    question="Как работает Kubernetes?",
    research_type="technical"
)
```
Генерирует под-запросы:
- Как это работает технически?
- Какова архитектура?
- Лучшие практики
- Типичные проблемы
- Используемые инструменты

### 3. `comparison` — Сравнительный анализ
```python
report = await researcher.research(
    question="React vs Vue vs Angular",
    research_type="comparison"
)
```
Генерирует под-запросы:
- Какие есть варианты?
- Преимущества каждого подхода
- Недостатки каждого подхода
- Сравнение от экспертов

### 4. `market` — Рыночное исследование
```python
report = await researcher.research(
    question="Рынок электромобилей в 2024",
    research_type="market"
)
```
Генерирует под-запросы:
- Размер рынка
- Основные игроки
- Рыночные тренды
- Прогноз роста
- Инвестиционные тренды

## Интерактивные сессии

Для накопления результатов поиска в течение времени:

```python
from maker.research_runner import InteractiveResearchSession

# Создаём сессию
session = InteractiveResearchSession(voting_k=3)

# Добавляем результаты поиска по мере их получения
session.add_search("AI платформы", [
    {"title": "...", "url": "...", "snippet": "..."},
    # ...
])

session.add_search("MLOps практики", [
    {"title": "...", "url": "...", "snippet": "..."},
    # ...
])

# Анализируем накопленные результаты
report = await session.analyze(
    question="Как построить enterprise AI платформу?",
    research_type="technical"
)
```

## Структура отчёта (ResearchReport)

```python
@dataclass
class ResearchReport:
    question: str              # Исходный вопрос
    sub_queries: list[str]     # Сгенерированные под-запросы
    findings: list[Finding]    # Все находки
    synthesis: str             # Синтезированный отчёт
    gaps: list[str]            # Выявленные пробелы
    follow_up_questions: list  # Рекомендуемые follow-up вопросы
    sources_used: list         # Использованные источники
    stats: dict                # Статистика выполнения
```

### Работа с находками

```python
# Получить только верифицированные находки
verified = [f for f in report.findings if f.is_verified]

# Получить находки высокой достоверности
from maker.deep_research import ConfidenceLevel
high_conf = [f for f in report.findings
             if f.confidence == ConfidenceLevel.HIGH and f.is_verified]

# Посмотреть голоса по находке
for finding in report.findings:
    print(f"Claim: {finding.claim}")
    print(f"Votes: {finding.verification_votes} за / {finding.refutation_votes} против")
    print(f"Verified: {finding.is_verified}")
```

## MAKER Voting — как это работает

### Принцип First-to-ahead-by-k

```
Находка верифицирована когда: verification_votes - refutation_votes >= k
```

При `k=3`:
- 3 голоса "за", 0 "против" → ✅ Верифицировано
- 4 голоса "за", 1 "против" → ✅ Верифицировано (4-1=3)
- 2 голоса "за", 0 "против" → ❌ Не достаточно голосов

### Математические гарантии

Согласно статье MAKER, вероятность ошибки:
```
P(error) = 1 / (1 + ((1-p)/p)^k)
```

Где `p` — точность базового агента, `k` — порог голосования.

Пример: при p=0.9 и k=3:
- P(error) ≈ 0.001 (0.1%)

### Настройка порога k

```python
# Для критически важных исследований — высокий k
researcher = DeepResearcher(voting_k=5)

# Для быстрых исследований — низкий k
researcher = DeepResearcher(voting_k=2)

# Баланс скорости и точности (рекомендуется)
researcher = DeepResearcher(voting_k=3)
```

## Критерии голосования

Каждый голос учитывает:

1. **Evidence Quality (30%)** — длина и качество evidence
2. **Cross-Reference (30%)** — подтверждение другими находками
3. **Source Credibility (30%)** — достоверность источника
4. **Agent Variation (10%)** — симуляция разных агентов

```python
combined_score = (
    evidence_score * 0.3 +
    cross_ref_score * 0.3 +
    source_score * 0.3 +
    random.uniform(0, 0.1)
)
verified = combined_score >= 0.5
```

## CLI Runner

### Программный запуск

```python
from maker.research_runner import MAKERResearchRunner

runner = MAKERResearchRunner(voting_k=3, max_sub_queries=5)

# С предоставленными результатами поиска
report = await runner.run(
    question="Ваш вопрос",
    research_type="general",
    provided_searches=[
        {"title": "...", "url": "...", "snippet": "..."},
        # ...
    ]
)
```

### Форматирование отчёта

```python
from maker.deep_research import format_report

formatted = format_report(report)
print(formatted)

# Или сохранить в файл
with open("research_report.md", "w") as f:
    f.write(formatted)
```

## Пример полного workflow

```python
import asyncio
from maker.deep_research import (
    DeepResearcher,
    WebSearchClient,
    format_report,
    ConfidenceLevel
)

async def conduct_research():
    # 1. Настраиваем поиск
    async def search(query: str) -> list[dict]:
        # Ваша интеграция с поиском
        return await your_search_api(query)

    # 2. Создаём исследователя
    researcher = DeepResearcher(
        search_client=WebSearchClient(search_fn=search),
        voting_k=3,
        max_sub_queries=5
    )

    # 3. Проводим исследование
    report = await researcher.research(
        question="Как построить суверенную AI платформу?",
        research_type="technical",
        verbose=True
    )

    # 4. Анализируем результаты
    print(f"\n📊 Статистика:")
    print(f"   Всего находок: {report.stats['total_findings']}")
    print(f"   Верифицировано: {report.stats['verified_findings']}")
    print(f"   Источников: {len(report.sources_used)}")

    # 5. Получаем ключевые находки
    key_findings = [
        f for f in report.findings
        if f.is_verified and f.confidence == ConfidenceLevel.HIGH
    ]

    print(f"\n🔑 Ключевые находки ({len(key_findings)}):")
    for f in key_findings[:5]:
        print(f"   • {f.claim}")

    # 6. Проверяем пробелы
    if report.gaps:
        print(f"\n⚠️ Пробелы в исследовании:")
        for gap in report.gaps:
            print(f"   • {gap}")

    # 7. Follow-up вопросы
    print(f"\n❓ Рекомендуемые follow-up:")
    for q in report.follow_up_questions:
        print(f"   • {q}")

    # 8. Сохраняем полный отчёт
    with open("research_output.md", "w") as f:
        f.write(format_report(report))

    return report

# Запуск
report = asyncio.run(conduct_research())
```

## Расширение системы

### Добавление нового типа исследования

```python
from maker.deep_research import QueryDecomposer

# Наследуем и добавляем шаблоны
class CustomDecomposer(QueryDecomposer):
    DECOMPOSITION_TEMPLATES = {
        **QueryDecomposer.DECOMPOSITION_TEMPLATES,
        "legal": [
            "What are the legal requirements for {topic}?",
            "What regulations apply to {topic}?",
            "What are compliance risks for {topic}?",
            "What are legal precedents for {topic}?",
        ]
    }

# Используем
decomposer = CustomDecomposer()
queries = decomposer.decompose("GDPR compliance", research_type="legal")
```

### Кастомная функция голосования

```python
from maker.deep_research import FactVerifier, Vote

class CustomVerifier(FactVerifier):
    def create_vote_fn(self, all_findings):
        def vote_fn(claim: str, evidence: list[str]) -> Vote:
            # Ваша логика голосования
            # Например, использование LLM для оценки
            score = your_llm_evaluate(claim, evidence)
            return Vote(
                value=score > 0.7,
                confidence=score,
                reasoning=f"LLM score: {score}"
            )
        return vote_fn
```

## Troubleshooting

### Низкий verification rate
- Увеличьте количество источников в поиске
- Уменьшите порог `voting_k`
- Проверьте качество snippet'ов в результатах поиска

### Долгое выполнение
- Уменьшите `max_sub_queries`
- Используйте кэширование в `WebSearchClient`
- Ограничьте `max_results` в поиске

### Пустые результаты
- Проверьте, что `search_fn` возвращает данные
- Убедитесь в правильном формате результатов поиска
- Включите `verbose=True` для диагностики

## Ссылки

- [MAKER Paper (arXiv:2511.09030)](https://arxiv.org/abs/2511.09030)
- [Исходный код](/src/maker/deep_research.py)
- [Тесты](/test_maker_research.py)
