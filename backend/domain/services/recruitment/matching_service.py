import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from core.config import settings

logger = logging.getLogger(__name__)


# ── Structured output schema (spec §3.2) ─────────────────────────────────────
class RankedDepartment(BaseModel):
    department_id: int = Field(description="The department id being ranked")
    confidence: float = Field(description="Fit confidence from 0.0 to 1.0")
    rationale: str = Field(description="Two sentences max explaining the fit")


class MatchOutput(BaseModel):
    ranked_departments: list[RankedDepartment] = Field(
        description="Departments ranked best-fit first"
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Optional flags, e.g. 'cv_unreadable'",
    )


class RecruitmentMatchingService:
    """
    One structured-output LLM call per application (NOT a multi-agent system).
    Compares the candidate's answers + extracted CV text against the active
    departments and returns a ranked fit. Failure-tolerant: callers treat any
    exception as 'matching pending/failed' and never lose the application.
    """

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-5-mini", temperature=1.0, api_key=settings.OPENAI_API_KEY)
        self.parser = JsonOutputParser(pydantic_object=MatchOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a recruitment matching assistant for a student consulting "
             "association. Given a candidate's application and the open departments, "
             "estimate how well the candidate fits EACH department. Base your judgement "
             "on the department descriptions and the skills they seek. Be encouraging "
             "but honest. Return ONLY the structured JSON.\n{format_instructions}"),
            ("human",
             "DEPARTMENTS:\n{departments}\n\n"
             "CANDIDATE APPLICATION:\n"
             "Applied for department id: {applied_department_id}\n"
             "Degree: {degree} | Year: {year}\n"
             "Answers: {answers}\n\n"
             "CV TEXT (may be empty if unreadable):\n{cv_text}\n\n"
             "Rank every department by fit (best first) with a confidence 0-1 and a "
             "two-sentence rationale. If the CV text is empty, add the flag "
             "'cv_unreadable' and judge on the answers alone."),
        ]).partial(format_instructions=self.parser.get_format_instructions())
        self.chain = self.prompt | self.llm | self.parser

    def _departments_blurb(self, departments) -> str:
        lines = []
        for d in departments:
            skills = ", ".join(d.skills_sought or [])
            lines.append(f"- id={d.department_id} | {d.name}: {d.description or ''} (skills: {skills})")
        return "\n".join(lines)

    def match(self, *, applied_department_id, degree, year, answers, cv_text, departments) -> dict:
        """Run the matching call. Returns a MatchOutput-shaped dict. Raises on LLM failure."""
        result = self.chain.invoke({
            "departments": self._departments_blurb(departments),
            "applied_department_id": applied_department_id,
            "degree": degree or "unknown",
            "year": year or "unknown",
            "answers": str(answers or {}),
            "cv_text": (cv_text or "")[:12000],
        })
        # Keep only ranks for departments that actually exist, sorted by confidence.
        valid_ids = {d.department_id for d in departments}
        ranked = [r for r in result.get("ranked_departments", []) if r.get("department_id") in valid_ids]
        ranked.sort(key=lambda r: r.get("confidence", 0), reverse=True)
        flags = result.get("flags", [])
        if not cv_text and "cv_unreadable" not in flags:
            flags.append("cv_unreadable")
        return {"ranked_departments": ranked, "flags": flags}


# Lazy singleton so importing this module doesn't construct the LLM client
# (which would happen at app import time and slow startup).
_service: RecruitmentMatchingService | None = None


def get_matching_service() -> RecruitmentMatchingService:
    global _service
    if _service is None:
        _service = RecruitmentMatchingService()
    return _service
