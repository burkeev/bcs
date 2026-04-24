"""
Сервисы чат-пайплайна: RAG-поиск и интеграция с Gemini.

Модуль содержит:

* :class:`RAGService` — семантический поиск фрагментов НПА в ChromaDB.
* :class:`ChatService` — оркестратор: получает контекст у RAG, формирует
  промпт и вызывает LLM. Параметры генерации (system prompt,
  temperature, max_tokens) передаются извне — обычно из админской
  конфигурации :class:`app.models.BotConfig`.
* Глобальный экземпляр :data:`chat_service`, переиспользуемый между
  HTTP-запросами (чтобы не пересоздавать клиенты ChromaDB и Gemini).
"""

import os

import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


# ==========================================
# 1. RAG Service (Поиск по базе знаний)
# ==========================================
class RAGService:
    """Семантический поиск по нормативно-правовым актам.

    Поверх локального persistent-клиента ChromaDB. Тексты НПА хранятся
    в коллекции ``legal_materials``; векторизация — встроенной моделью
    эмбеддингов ChromaDB.

    Attributes:
        chroma_client: Persistent-клиент ChromaDB.
        collection: Коллекция с фрагментами НПА.
    """

    def __init__(self, db_path: str = "./chroma_data"):
        """Открывает (или создаёт) коллекцию ``legal_materials``.

        Args:
            db_path: Путь к папке с векторным индексом.
        """
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="legal_materials"
        )

    def add_material(self, doc_id: str, text: str, source: str) -> None:
        """Добавляет фрагмент НПА в векторную базу.

        Args:
            doc_id: Уникальный идентификатор документа.
            text: Текст фрагмента.
            source: Человекочитаемое имя источника (попадёт в metadata).
        """
        self.collection.add(
            documents=[text],
            metadatas=[{"source": source}],
            ids=[str(doc_id)],
        )

    def delete_material(self, doc_id: str) -> None:
        """Удаляет фрагмент НПА из векторной базы по идентификатору.

        Используется админ-сервисом при удалении НПА из основной БД,
        чтобы поддерживать консистентность между PostgreSQL и ChromaDB.

        Args:
            doc_id: Идентификатор документа.
        """
        self.collection.delete(ids=[str(doc_id)])

    def search_context(self, query: str, n_results: int = 2) -> str:
        """Ищет фрагменты НПА, семантически близкие к запросу.

        Args:
            query: Вопрос пользователя.
            n_results: Сколько фрагментов вернуть (default: 2).

        Returns:
            str: Склеенный контекст с префиксами-источниками,
            либо пустая строка, если в коллекции ничего не найдено.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            source = results["metadatas"][0][i].get(
                "source", "Неизвестный источник"
            )
            chunks.append(f"[{source}]: {doc}")

        return "\n\n".join(chunks)


# ==========================================
# 2. Chat Service (RAG + LLM Gemini)
# ==========================================
class ChatService:
    """Оркестратор пайплайна "вопрос -> RAG -> LLM -> ответ".

    Attributes:
        model: Клиент ``GenerativeModel`` Gemini.
        rag_service: Экземпляр :class:`RAGService`.
    """

    def __init__(self):
        """Инициализирует клиент Gemini и RAG-сервис.

        Ключ API читается из ``GEMINI_API_KEY``. При его отсутствии
        пишется предупреждение, но исключение не выбрасывается —
        чтобы приложение могло стартовать (ошибка всплывёт уже при
        генерации ответа).
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print(
                "ВНИМАНИЕ: API ключ GEMINI_API_KEY не найден в .env"
            )

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        self.rag_service = RAGService()

    def process_query(
        self,
        user_query: str,
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict:
        """Полный цикл обработки запроса пользователя.

        Шаги:

        1. Поиск релевантного контекста через :class:`RAGService`.
        2. Сборка промпта (с контекстом или fallback без него).
        3. Вызов Gemini с указанными параметрами генерации.

        Args:
            user_query: Вопрос пользователя.
            system_prompt: Системная инструкция для LLM.
            temperature: Параметр генерации (низкое значение —
                более детерминированные ответы).
            max_tokens: Максимальная длина ответа в токенах.

        Returns:
            dict: ``{"reply": str, "has_references": bool, "used_context": str}``.
        """
        context = self.rag_service.search_context(user_query)

        if context:
            full_prompt = (
                f"{system_prompt}\n\n"
                f"КОНТЕКСТ (Выдержки из законов):\n{context}\n\n"
                f"ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_query}\n\n"
                f"ОТВЕТЬ НА ОСНОВЕ КОНТЕКСТА."
            )
        else:
            full_prompt = (
                f"{system_prompt}\n\n"
                f"ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_query}\n\n"
                f"ОТВЕТЬ КАК ЮРИСТ, ДАЖЕ ЕСЛИ НЕТ КОНТЕКСТА."
            )

        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            bot_reply = response.text
        except Exception as e:
            bot_reply = f"Ошибка связи с LLM: {str(e)}"

        return {
            "reply": bot_reply,
            "has_references": bool(context),
            "used_context": context,
        }


# Единый экземпляр сервиса на всё приложение.
chat_service = ChatService()