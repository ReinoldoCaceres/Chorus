from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain.schema import Document
from typing import List, Dict, Any, Tuple
import structlog
import re

from app.config import get_settings
from app.models.schemas import SummaryType

logger = structlog.get_logger()
settings = get_settings()


class SummaryService:
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=settings.openai_api_key,
            model_name=settings.openai_model,
            temperature=settings.summary_temperature,
            max_tokens=settings.max_tokens
        )
        logger.info("Summary service initialized")
    
    async def generate_summary(
        self,
        messages: List[str],
        summary_type: SummaryType,
        max_length: int = 500,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate summary based on conversation messages"""
        try:
            # Combine messages into a single document
            text = "\n".join(messages)
            docs = [Document(page_content=text)]
            
            # Select appropriate prompt template
            prompt_template = self._get_prompt_template(summary_type, max_length)
            
            # Create summarization chain
            chain = load_summarize_chain(
                llm=self.llm,
                chain_type="stuff",
                prompt=prompt_template
            )
            
            # Generate summary
            result = await chain.arun(docs)
            
            # Post-process based on summary type
            processed_result = self._post_process_summary(result, summary_type)
            
            logger.info("Summary generated successfully",
                       summary_type=summary_type.value,
                       input_length=len(text),
                       output_length=len(processed_result.get("summary", "")))
            
            return processed_result
            
        except Exception as e:
            logger.error("Summary generation failed",
                        summary_type=summary_type.value,
                        error=str(e))
            raise
    
    def _get_prompt_template(self, summary_type: SummaryType, max_length: int) -> PromptTemplate:
        """Get appropriate prompt template based on summary type"""
        
        base_instruction = f"Please provide a summary in approximately {max_length} characters."
        
        if summary_type == SummaryType.CONVERSATION:
            template = f"""
            {base_instruction}
            
            Summarize the following conversation, capturing the main topics discussed, 
            key decisions made, and important information exchanged:
            
            {{text}}
            
            CONVERSATION SUMMARY:
            """
        
        elif summary_type == SummaryType.TOPIC:
            template = f"""
            {base_instruction}
            
            Analyze the following conversation and identify the main topics discussed.
            Provide a structured summary organized by topic:
            
            {{text}}
            
            TOPIC SUMMARY:
            """
        
        elif summary_type == SummaryType.SENTIMENT:
            template = f"""
            {base_instruction}
            
            Analyze the sentiment and emotional tone of the following conversation.
            Include overall sentiment, key emotional moments, and participant attitudes:
            
            {{text}}
            
            SENTIMENT ANALYSIS:
            """
        
        elif summary_type == SummaryType.KEY_POINTS:
            template = f"""
            {base_instruction}
            
            Extract the key points, action items, and important takeaways from 
            the following conversation:
            
            {{text}}
            
            KEY POINTS:
            """
        
        else:
            template = f"""
            {base_instruction}
            
            Provide a comprehensive summary of the following conversation:
            
            {{text}}
            
            SUMMARY:
            """
        
        return PromptTemplate(template=template, input_variables=["text"])
    
    def _post_process_summary(self, raw_summary: str, summary_type: SummaryType) -> Dict[str, Any]:
        """Post-process the generated summary based on type"""
        result = {
            "summary": raw_summary.strip(),
            "key_topics": [],
            "sentiment": None,
            "confidence_score": None,
            "metadata": {}
        }
        
        try:
            # Extract key topics using simple keyword extraction
            result["key_topics"] = self._extract_topics(raw_summary)
            
            # Extract sentiment if it's a sentiment analysis
            if summary_type == SummaryType.SENTIMENT:
                result["sentiment"] = self._extract_sentiment(raw_summary)
            
            # Calculate confidence score (simplified)
            result["confidence_score"] = self._calculate_confidence(raw_summary)
            
        except Exception as e:
            logger.warning("Post-processing failed", error=str(e))
        
        return result
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract key topics from summary text"""
        # Simple topic extraction using common patterns
        topics = []
        
        # Look for common topic indicators
        topic_patterns = [
            r"topic[s]?[:\-\s]+([^.!?]+)",
            r"discuss[^.!?]*?(?:about|regarding|concerning)\s+([^.!?]+)",
            r"main\s+(?:subject|theme|focus)[^.!?]*?:\s*([^.!?]+)",
        ]
        
        for pattern in topic_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            topics.extend([match.strip() for match in matches])
        
        # Remove duplicates and limit to top 5
        unique_topics = list(set(topics))[:5]
        return [topic for topic in unique_topics if len(topic) > 3]
    
    def _extract_sentiment(self, text: str) -> str:
        """Extract overall sentiment from text"""
        text_lower = text.lower()
        
        positive_indicators = ["positive", "happy", "satisfied", "pleased", "good", "great", "excellent"]
        negative_indicators = ["negative", "unhappy", "dissatisfied", "frustrated", "bad", "poor", "terrible"]
        neutral_indicators = ["neutral", "mixed", "balanced", "objective"]
        
        positive_count = sum(1 for word in positive_indicators if word in text_lower)
        negative_count = sum(1 for word in negative_indicators if word in text_lower)
        neutral_count = sum(1 for word in neutral_indicators if word in text_lower)
        
        if neutral_count > 0 or (positive_count == negative_count):
            return "neutral"
        elif positive_count > negative_count:
            return "positive"
        else:
            return "negative"
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score based on summary quality indicators"""
        # Simple heuristic based on text characteristics
        score = 0.5  # Base score
        
        # Length appropriateness
        if 100 <= len(text) <= 1000:
            score += 0.2
        
        # Presence of specific information
        if any(word in text.lower() for word in ["discussed", "decided", "agreed", "concluded"]):
            score += 0.1
        
        # Structure indicators
        if any(char in text for char in [":", "-", "•"]):
            score += 0.1
        
        # Avoid overly generic responses
        generic_phrases = ["the conversation", "participants discussed", "various topics"]
        if not any(phrase in text.lower() for phrase in generic_phrases):
            score += 0.1
        
        return min(1.0, score)