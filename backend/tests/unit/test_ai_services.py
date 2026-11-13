"""
The AI services (LangChain + OpenAI SDK + sentence-transformers), exercised
without the network. OpenAI is replaced at the HTTP layer, so the real client
code runs: which endpoint it calls, what it sends, and how the reply is parsed
all have to keep working when these libraries are upgraded.
"""
import asyncio
import json
import os
from types import SimpleNamespace

import httpx
import pytest
from langchain_openai import ChatOpenAI

from domain.services.ai import chat_service as chat_module
from domain.services.ai.chat_service import ChatService
from domain.services.ai.document_vectorization_service import DocumentVectorizationService
from domain.services.ai.feedback_summary_service import FeedbackSummaryService
from domain.services.recruitment.matching_service import RecruitmentMatchingService


class FakeOpenAI:
    """Answers chat-completion requests with `reply`, and keeps what was asked."""

    def __init__(self, reply="", status=200):
        self.reply = reply
        self.status = status
        self.requests = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append((request.url.path, body))
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "boom", "type": "server_error"}})
        if body.get("stream"):
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=self._stream())
        return httpx.Response(200, json={
            "id": "chatcmpl-test", "object": "chat.completion", "created": 0, "model": body["model"],
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": self.reply}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    def _stream(self) -> bytes:
        def event(delta, finish=None):
            chunk = {"id": "chatcmpl-test", "object": "chat.completion.chunk", "created": 0, "model": "gpt-5-mini",
                     "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
            return f"data: {json.dumps(chunk)}\n\n"

        pieces = self.reply.split(" ")
        words = [word + " " for word in pieces[:-1]] + pieces[-1:]
        events = [event({"role": "assistant", "content": ""})]
        events += [event({"content": word}) for word in words]
        events += [event({}, finish="stop"), "data: [DONE]\n\n"]
        return "".join(events).encode()

    def llm(self, **kwargs) -> ChatOpenAI:
        return ChatOpenAI(
            model="gpt-5-mini", temperature=1.0, api_key="test", max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(self.handle)),
            http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(self.handle)),
            **kwargs,
        )

    @property
    def prompt(self) -> str:
        return "\n".join(str(message["content"]) for message in self.requests[-1][1]["messages"])


def department(department_id, name, **fields):
    values = {"description": f"{name} work", "skills_sought": [], "scoring_criteria": []}
    return SimpleNamespace(department_id=department_id, name=name, **{**values, **fields})


# --- recruitment matching ---------------------------------------------------

class TestMatching:
    @pytest.fixture
    def openai(self):
        return FakeOpenAI()

    @pytest.fixture
    def service(self, openai):
        service = RecruitmentMatchingService()
        service.llm = openai.llm()
        service.chain = service.prompt | service.llm | service.parser
        return service

    def match(self, service, **overrides):
        arguments = {
            "applied_department_id": 1, "degree": "BBA", "year": "2", "answers": {"why": "I like data"},
            "cv_text": "Jane Candidate, analyst", "departments": [department(1, "Data"), department(2, "Events")],
        }
        return service.match(**{**arguments, **overrides})

    def test_ranks_come_back_sorted_and_limited_to_real_departments(self, service, openai):
        openai.reply = json.dumps({"ranked_departments": [
            {"department_id": 2, "confidence": 0.4, "rationale": "Some fit."},
            {"department_id": 99, "confidence": 0.99, "rationale": "Invented."},
            {"department_id": 1, "confidence": 0.9, "rationale": "Strong fit."},
        ], "flags": []})

        result = self.match(service)

        assert [r["department_id"] for r in result["ranked_departments"]] == [1, 2]
        assert result["flags"] == []

    def test_json_wrapped_in_a_code_fence_is_still_parsed(self, service, openai):
        openai.reply = '```json\n{"ranked_departments": [{"department_id": 1, "confidence": 0.7, "rationale": "Fits."}], "flags": []}\n```'

        assert self.match(service)["ranked_departments"][0]["department_id"] == 1

    def test_missing_cv_is_flagged(self, service, openai):
        openai.reply = json.dumps({"ranked_departments": [], "flags": []})

        assert self.match(service, cv_text=None)["flags"] == ["cv_unreadable"]

    def test_the_request_is_a_chat_completion_carrying_the_application(self, service, openai):
        openai.reply = json.dumps({"ranked_departments": [], "flags": []})
        departments = [department(1, "Data", skills_sought=["SQL"], scoring_criteria=[{"label": "Motivation", "weight": 60}])]

        self.match(service, departments=departments)

        path, body = openai.requests[-1]
        assert path.endswith("/chat/completions")
        assert body["model"] == "gpt-5-mini"
        assert [message["role"] for message in body["messages"]] == ["system", "user"]
        assert "id=1 | Data: Data work Skills sought: SQL. Scored on: Motivation (60%)." in openai.prompt
        assert "Jane Candidate, analyst" in openai.prompt
        assert "ranked_departments" in openai.prompt  # the format instructions

    def test_openai_failing_raises_instead_of_inventing_a_match(self, service, openai):
        openai.status = 500

        with pytest.raises(Exception):
            self.match(service)

    def test_a_reply_that_isnt_json_raises(self, service, openai):
        openai.reply = "Sorry, I can't help with that."

        with pytest.raises(Exception):
            self.match(service)


# --- feedback summary -------------------------------------------------------

class TestFeedbackSummary:
    SUMMARY = {
        "executive_summary": "People liked it.", "key_highlights": ["Speakers"], "areas_for_improvement": ["Food"],
        "sentiment": "positive", "sentiment_score": 8.5, "notable_quotes": ["Great!"],
        "recommendations": ["More food"], "themes": ["Networking"],
    }

    @pytest.fixture
    def openai(self):
        return FakeOpenAI(reply=json.dumps(self.SUMMARY))

    @pytest.fixture
    def service(self, openai):
        service = FeedbackSummaryService()
        service.llm = openai.llm()
        service.chain = service.prompt | service.llm | service.parser
        return service

    def summarise(self, service):
        return service.generate_summary(
            event_name="Data Night", event_type="workshop", response_count=1, response_rate=50.0,
            template_fields=[{"type": "rating", "label": "Overall", "name": "overall"}],
            feedback_response=[{"overall": 5}],
        )

    def test_summary_is_parsed_and_stamped(self, service, openai):
        result = self.summarise(service)

        assert {key: result[key] for key in self.SUMMARY} == self.SUMMARY
        assert result["model_used"] == "gpt-5-mini"
        assert result["generated_at"]
        assert openai.requests[-1][0].endswith("/chat/completions")
        assert "Data Night" in openai.prompt

    def test_failure_is_reported_not_swallowed(self, service, openai):
        openai.status = 500

        with pytest.raises(Exception, match="Failed to generate AI summary"):
            self.summarise(service)


# --- document chunking ------------------------------------------------------

class TestChunking:
    @pytest.fixture
    def service(self):
        return DocumentVectorizationService(qdrant_client=None, collection_name="test")

    def test_children_are_small_pieces_of_their_parent(self, service):
        text = "\n\n".join(f"Paragraph {n}. " + "Ennova runs events for students. " * 12 for n in range(20))

        chunks = service.get_parent_child_chunks(text)

        parents = {chunk["parent_content"] for chunk in chunks}
        assert len(parents) > 1
        assert len(chunks) > len(parents)
        for chunk in chunks:
            assert len(chunk["parent_content"]) <= 2000
            assert len(chunk["child_content"]) <= 400
            assert chunk["child_content"] in chunk["parent_content"]

    def test_nothing_is_lost(self, service):
        text = " ".join(f"word{n}" for n in range(1500))

        covered = " ".join(chunk["child_content"] for chunk in service.get_parent_child_chunks(text))

        assert all(f"word{n}" in covered for n in range(1500))

    def test_short_text_is_one_chunk_and_empty_text_is_none(self, service):
        assert service.get_parent_child_chunks("Just one line.") == [
            {"child_content": "Just one line.", "parent_content": "Just one line."}
        ]
        assert service.get_parent_child_chunks("") == []


# --- chat -------------------------------------------------------------------

def hit(content, parent, filename="handbook.docx"):
    return SimpleNamespace(payload={"content": content, "full_context": parent, "filename": filename})


class FakeQdrant:
    def __init__(self, hits):
        self.hits = hits
        self.queries = []

    def query_points(self, **kwargs):
        self.queries.append(kwargs)
        return SimpleNamespace(points=self.hits)


class FakeEmbeddings:
    async def aembed_query(self, query):
        return [0.1, 0.2, 0.3]


class FakeSession:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def query(self, model):
        return SimpleNamespace(filter=lambda *a: SimpleNamespace(first=lambda: None))


class TestChat:
    @pytest.fixture
    def openai(self):
        return FakeOpenAI(reply="Ennova meets on Tuesdays.")

    @pytest.fixture
    def qdrant(self):
        return FakeQdrant([
            hit("about parking", "PARENT parking"),
            hit("meeting times", "PARENT meetings"),
            hit("more on meetings", "PARENT meetings"),
        ])

    @pytest.fixture
    def service(self, openai, qdrant, monkeypatch):
        service = ChatService(qdrant_client=qdrant, collection_name="test")
        service.embeddings = FakeEmbeddings()
        service.llm = openai.llm(streaming=True)
        # Scores by keyword, so the order is known without loading the real model.
        reranker = SimpleNamespace(predict=lambda pairs: [2.0 if "meeting" in text else -3.0 for _, text in pairs])
        monkeypatch.setattr(chat_module, "get_reranker", lambda: reranker)
        return service

    def test_context_is_reranked_and_parents_arent_repeated(self, service, qdrant):
        context = asyncio.run(service.retrieve_context("when are the meetings?"))

        assert [chunk["content"] for chunk in context] == ["PARENT meetings", "PARENT parking"]
        assert context[0] == {"content": "PARENT meetings", "filename": "handbook.docx", "score": 2.0}
        assert qdrant.queries[0]["query"] == [0.1, 0.2, 0.3]
        assert qdrant.queries[0]["limit"] == 25

    def test_no_hits_means_no_context(self, service, qdrant):
        qdrant.hits = []

        assert asyncio.run(service.retrieve_context("anything")) == []

    def test_answer_is_streamed_as_text_and_both_messages_are_saved(self, service, openai):
        session = FakeSession()
        history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]

        async def collect():
            return [piece async for piece in service.generate_response("When do you meet?", 7, history, session)]

        pieces = asyncio.run(collect())

        assert all(isinstance(piece, str) for piece in pieces)
        assert "".join(pieces) == "Ennova meets on Tuesdays."
        assert len([piece for piece in pieces if piece]) > 1  # really streamed, not one blob

        path, body = openai.requests[-1]
        assert path.endswith("/chat/completions")
        assert body["stream"] is True
        assert [message["role"] for message in body["messages"]] == ["system", "user", "assistant", "user"]
        assert body["messages"][-1]["content"] == "When do you meet?"
        assert "[handbook.docx] PARENT meetings" in body["messages"][0]["content"]

        user_message, assistant_message = session.added
        assert (user_message.role, user_message.content, user_message.chat_id) == ("user", "When do you meet?", 7)
        assert (assistant_message.role, assistant_message.content) == ("assistant", "Ennova meets on Tuesdays.")
        assert assistant_message.retrieved_chunks[0]["content"] == "PARENT meetings"
        assert session.rollbacks == 0

    def test_openai_failing_gives_an_apology_and_rolls_back(self, service, openai):
        openai.status = 500
        session = FakeSession()

        async def collect():
            return [piece async for piece in service.generate_response("Hi", 7, [], session)]

        assert asyncio.run(collect()) == ["I apologise, but I encountered an error. Please try again later."]
        assert session.rollbacks == 1

    def test_chat_title(self, service, openai):
        openai.reply = '"Meeting Times Question"'

        assert asyncio.run(service.create_chat_title("When do you meet?")) == "Meeting Times Question"


# --- the real reranker ------------------------------------------------------

RERANKER_CACHE = os.path.expanduser("~/.cache/huggingface/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2")


@pytest.mark.skipif(not os.path.isdir(RERANKER_CACHE), reason="reranker model isn't downloaded on this machine")
def test_real_reranker_scores_the_relevant_passage_highest(monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    chat_module.get_reranker.cache_clear()
    try:
        scores = chat_module.get_reranker().predict([
            ["When does Ennova meet?", "Ennova meets every Tuesday at 18:00 in room 204."],
            ["When does Ennova meet?", "Parking at the campus costs two euros per hour."],
        ])
    finally:
        chat_module.get_reranker.cache_clear()

    assert len(scores) == 2
    assert float(scores[0]) > float(scores[1])
