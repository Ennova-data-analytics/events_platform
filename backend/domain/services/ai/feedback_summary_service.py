from datetime import datetime 
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from core.config import settings
from typing import Any

class FeedbackSummaryOutput(BaseModel):
    """Structured output schema for feedback summary"""
    executive_summary: str = Field(description="2-3 sentence overview of the feedback")
    key_highlights: list[str] = Field(description="3-5 bullet points of positive feedback and strengths")
    areas_for_improvement: list[str] = Field(description="3-5 actionable insights for improvement")
    sentiment: str = Field(description="Overall sentiment: 'positive', 'neutral', or 'negative'")
    sentiment_score: float = Field(description="Sentiment score from 0 (very negative) to 10 (very positive)")
    notable_quotes: list[str] = Field(description="2-3 specific comments that stand out")
    recommendations: list[str] = Field(description="Specific actions the organiser should consider")
    themes: list[str] = Field(description="Key recurring themes, identified in the feedback")

class FeedbackSummaryService:
    """Service for generating AI-powered feedback summaries"""
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-5-mini",
            temperature=1.0,
            api_key=settings.OPENAI_API_KEY
        )

        self.parser = JsonOutputParser(pydantic_object=FeedbackSummaryOutput)
        self.prompt = self._create_prompt_template()
        self.chain = self.prompt | self.llm | self.parser
    

    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create the LangChain prompt template for feedback analysis"""
        
        system_message = """You are an expert event feedback analyst. Your role is to analyze
                            event feedback data and generate actionable insights for event organizers.

                            You must analyze the feedback thoroughly and provide:
                            1. Executive Summary - A brief overview of the overall feedback
                            2. Key Highlights - The most positive aspects and strengths
                            3. Areas for Improvement - Constructive criticism and opportunities
                            4. Sentiment Analysis - Overall tone and emotional response
                            5. Notable Quotes - Specific impactful comments
                            6. Recommendations - Concrete actions the organizer should take
                            7. Themes - Recurring topics or patterns in the feedback

                            Be objective, constructive, and focus on actionable insights.
                         """
        
        human_message = """Analyze the following event feedback data:

                            EVENT CONTEXT:
                            - Event Name: {event_name}
                            - Event Type: {event_type}
                            - Total Responses: {response_count}
                            - Response Rate: {response_rate}%

                            FEEDBACK TEMPLATE STRUCTURE:
                            {template_fields}

                            RAW FEEDBACK RESPONSES:
                            {feedback_data}

                            Generate a comprehensive analysis following this JSON schema:
                            {format_instructions}

                            Ensure all insights are specific, actionable, and based on the actual feedback data provided.
                        """
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", human_message)
        ])
    

    def generate_summary(self, event_name: str, event_type: str, response_count: int, response_rate: float, template_fields: list[dict[str, Any]], feedback_response: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate an AI summary of feedback responses"""
        try:
            fields_description = self._format_template_fields(template_fields)
            feedback_text = self._format_feedback_data(feedback_response)

            result = self.chain.invoke({
                "event_name": event_name,
                "event_type": event_type,
                "response_count": response_count,
                "response_rate": f"{response_rate:.1f}",
                "template_fields": fields_description,
                "feedback_data": feedback_text,
                "format_instructions": self.parser.get_format_instructions()
            })

            result["generated_at"] = datetime.utcnow().isoformat()
            result["model_used"] = "gpt-5-mini"

            return result
    
        except Exception as e:
            raise Exception(f"Failed to generate AI summary: {str(e)}")

    
    def _format_template_fields(self, fields: list[dict[str, Any]]) -> str:
        """Format template fields into a readable string"""
        lines = []

        for field in fields:
            field_type = field.get("type", "unknown")
            field_label = field.get("label", "Unamed field")
            field_name = field.get("name", "unamed")

            line = f"- {field_name} ({field_type}): {field_label}"

            if "options" in field and field["options"]:
                options_str = ", ".join([opt["label"]] for opt in field["options"])
                line += f" [Options: {options_str}]"
            
            lines.append(line)
        
        return "\n".join(lines)
    

    def _format_feedback_data(self, responses: list[dict[str, Any]]) -> str:
        """Format feedback responses into a redeable string"""
        if not responses:
            return "No responses available"
        
        lines = []

        for idx, response in enumerate(responses, 1):
            lines.append(f"\n===Response {idx} ===")
            
            submitted_at = response.get("submitted_at")
            is_anonymous = response.get("is_anonymous", False)

            lines.append(f"Submitted: {submitted_at}")
            lines.append(f"Anonymous: {'Yes' if is_anonymous else 'No'}")

            form_responses = response.get("form_responses", {})
            if form_responses:
                lines.append("\Responses:")
                for field_name, value in form_responses.items():
                    if value is not None and value != "":
                        lines.append(f"  {field_name}: {value}")
            
            lines.append("")
        
        return "\n".join(lines)
    

    def generate_summary_markdown(self, summary_json: dict[str, Any]) -> str:
        """
        Convert the structured JSON summary into formatted markdown.
        """
        md_lines = [
            "# Feedback Analysis Summary",
            "",
            "## Executive Summary",
            summary_json.get("executive_summary", ""),
            "",
            "## Key Highlights",
            ""
        ]

        for highlight in summary_json.get("key_highlights", []):
            md_lines.append(f"- {highlight}")

        md_lines.extend([
            "",
            "## Areas for Improvement",
            ""
        ])

        for area in summary_json.get("areas_for_improvement", []):
            md_lines.append(f"- {area}")

        sentiment = summary_json.get("sentiment", "neutral")
        sentiment_score = summary_json.get("sentiment_score", 5.0)

        md_lines.extend([
            "",
            "## Sentiment Analysis",
            f"**Overall Sentiment:** {sentiment.capitalize()} ({sentiment_score}/10)",
            "",
            "## Notable Quotes",
            ""
        ])

        for quote in summary_json.get("notable_quotes", []):
            md_lines.append(f"> {quote}")
            md_lines.append("")

        md_lines.extend([
            "## Key Themes",
            ""
        ])

        for theme in summary_json.get("themes", []):
            md_lines.append(f"- {theme}")

        md_lines.extend([
            "",
            "## Recommendations",
            ""
        ])

        for recommendation in summary_json.get("recommendations", []):
            md_lines.append(f"- {recommendation}")

        return "\n".join(md_lines)