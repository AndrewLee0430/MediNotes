"""
LLM as Judge - 质量评估系统

用于评估 LLM 生成的医学答案质量，确保准确性、完整性和安全性。

Author: MediNotes Team
Date: 2026-02-16
Version: 1.0
"""

import json
import asyncio
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import openai
import os


@dataclass
class Source:
    """来源文档数据类"""
    source_id: str
    content: str
    

class LLMJudge:
    """
    LLM Judge - 使用 LLM 评估另一个 LLM 的输出质量
    
    评估维度：
    1. Accuracy (准确性) - 35%
    2. Completeness (完整性) - 25%
    3. Relevance (相关性) - 20%
    4. Source Support (来源支持) - 15%
    5. Safety (安全性) - 5%
    """
    
    # 评估维度权重
    WEIGHTS = {
        "accuracy": 0.35,
        "completeness": 0.25,
        "relevance": 0.20,
        "source_support": 0.15,
        "safety": 0.05
    }
    
    # 质量阈值
    THRESHOLDS = {
        "high": 80,      # >= 80: 高质量，直接使用
        "medium": 60,    # 60-79: 中等质量，添加警告
        "low": 0         # < 60: 低质量，重新生成
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化 LLM Judge"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        openai.api_key = self.api_key
    
    def _build_judge_prompt(
        self, 
        query: str, 
        answer: str, 
        sources: List[Source]
    ) -> str:
        """
        构建评估 Prompt
        
        Args:
            query: 用户的原始问题
            answer: LLM 生成的答案
            sources: 原始参考资料
            
        Returns:
            完整的评估 prompt
        """
        # 构建来源文本（限制每个来源250字符）
        sources_text = "\n\n".join([
            f"[Source {i+1}] {source.source_id}:\n{source.content[:250]}..."
            for i, source in enumerate(sources[:5])  # 最多5个来源
        ])
        
        prompt = f"""You are a medical fact-checking expert. Your task is to evaluate the quality of a medical answer.

# User Question
{query}

# Generated Answer
{answer}

# Available Reference Sources
{sources_text}

---

# Evaluation Task

Please evaluate the answer quality based on the provided reference sources.

## Evaluation Dimensions

1. **Accuracy** (0-100)
   - Are the facts in the answer consistent with the reference sources?
   - Are there any contradictions with the sources?
   - Scoring:
     * 100: All facts are supported by sources, completely accurate
     * 75: Mostly accurate, minor unsupported details
     * 50: Partially accurate, some unsupported claims
     * 25: Mostly inaccurate or contradicts sources
     * 0: Completely inaccurate or fabricated

2. **Completeness** (0-100)
   - Does the answer fully address the question?
   - Are all important aspects covered?
   - Scoring:
     * 100: Fully answers, covers all aspects
     * 75: Answers most, minor gaps
     * 50: Partial answer, missing important info
     * 25: Barely answers the question
     * 0: Does not answer at all

3. **Relevance** (0-100)
   - Is the answer relevant to the query?
   - Is there any off-topic content?
   - Scoring:
     * 100: Highly relevant, directly addresses query
     * 75: Mostly relevant, some tangential info
     * 50: Partially relevant, includes off-topic content
     * 25: Barely relevant
     * 0: Completely irrelevant

4. **Source Support** (0-100)
   - Can every claim in the answer be found in the sources?
   - Are there any hallucinations (unsupported content)?
   - Scoring:
     * 100: All claims directly supported by sources
     * 75: Most claims supported, minor unsupported details
     * 50: Partially supported, partially unsupported
     * 25: Minimal support, mostly unsupported
     * 0: No source support, likely hallucinations

5. **Safety** (0-100)
   - Does the answer include appropriate medical disclaimers?
   - Is it safe for medical reference?
   - Scoring:
     * 100: Includes appropriate medical disclaimer
     * 50: Partial disclaimer or implied warning
     * 0: No disclaimer, potentially misleading

## Important Notes
- If the answer contains specific data, percentages, or drug names NOT in the sources, mark as "hallucination"
- If the answer's conclusion contradicts the sources, give low score
- The answer should be based on sources, not imagination

## Response Format

Return ONLY a JSON object with this exact structure (no markdown formatting):

{{
  "scores": {{
    "accuracy": <0-100>,
    "completeness": <0-100>,
    "relevance": <0-100>,
    "source_support": <0-100>,
    "safety": <0-100>
  }},
  "issues": [
    "List of specific issues found (if any)"
  ],
  "has_hallucination": <true/false>,
  "recommendations": [
    "Specific recommendations for improvement (if score < 80)"
  ]
}}
"""
        return prompt
    
    async def evaluate(
        self,
        query: str,
        answer: str,
        sources: List[Source]
    ) -> Dict:
        """
        评估答案质量
        
        Args:
            query: 用户问题
            answer: 生成的答案
            sources: 参考来源
            
        Returns:
            评估结果字典
        """
        print(f"🔍 LLM Judge: Evaluating answer quality...")
        
        # 构建评估 prompt
        prompt = self._build_judge_prompt(query, answer, sources)
        
        try:
            # 调用 OpenAI API 进行评估
            response = await openai.ChatCompletion.acreate(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical fact-checking expert. Respond ONLY with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 较低温度以获得更一致的评估
                max_tokens=1000
            )
            
            # 解析评估结果
            content = response.choices[0].message.content.strip()
            
            # 移除可能的 markdown 代码块标记
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            evaluation = json.loads(content)
            
            # 计算加权分数
            scores = evaluation["scores"]
            weighted_score = sum(
                scores[dim] * self.WEIGHTS[dim]
                for dim in self.WEIGHTS.keys()
            )
            
            # 添加额外信息
            evaluation["weighted_score"] = round(weighted_score, 2)
            evaluation["overall_score"] = round(sum(scores.values()) / len(scores), 2)
            
            # 判断质量等级
            if weighted_score >= self.THRESHOLDS["high"]:
                evaluation["quality_level"] = "high"
            elif weighted_score >= self.THRESHOLDS["medium"]:
                evaluation["quality_level"] = "medium"
            else:
                evaluation["quality_level"] = "low"
            
            print(f"📊 Evaluation completed: Score = {weighted_score:.1f}/100")
            
            return evaluation
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Response content: {content[:200]}...")
            # 返回默认的低质量评估
            return self._get_default_evaluation(low_quality=True)
        except Exception as e:
            print(f"❌ Evaluation error: {e}")
            return self._get_default_evaluation(low_quality=True)
    
    def _get_default_evaluation(self, low_quality: bool = False) -> Dict:
        """返回默认评估结果（当评估失败时）"""
        if low_quality:
            return {
                "scores": {
                    "accuracy": 50,
                    "completeness": 50,
                    "relevance": 50,
                    "source_support": 50,
                    "safety": 50
                },
                "weighted_score": 50.0,
                "overall_score": 50.0,
                "quality_level": "medium",
                "issues": ["Evaluation failed, using default scores"],
                "has_hallucination": False,
                "recommendations": ["Manual review recommended"]
            }
        else:
            return {
                "scores": {
                    "accuracy": 75,
                    "completeness": 75,
                    "relevance": 75,
                    "source_support": 75,
                    "safety": 75
                },
                "weighted_score": 75.0,
                "overall_score": 75.0,
                "quality_level": "medium",
                "issues": [],
                "has_hallucination": False,
                "recommendations": []
            }
    
    def _build_warning(self, evaluation: Dict) -> str:
        """构建警告信息（中等质量时）"""
        issues = evaluation.get("issues", [])
        score = evaluation.get("weighted_score", 0)
        
        warning = f"\n\n⚠️ **Quality Notice** (Score: {score:.1f}/100)\n\n"
        warning += "This answer has been flagged with the following concerns:\n"
        
        for issue in issues[:3]:  # 最多显示3个问题
            warning += f"- {issue}\n"
        
        warning += "\n**Recommendation**: Please verify this information with a qualified healthcare professional.\n"
        
        return warning
    
    def _build_fallback(self, query: str, sources: List[Source]) -> str:
        """构建后备答案（低质量且重试失败时）"""
        fallback = f"I apologize, but I cannot provide a reliable answer to your question about '{query}' "
        fallback += "based on the available sources.\n\n"
        fallback += "**Available Information Sources**:\n"
        
        for i, source in enumerate(sources[:3], 1):
            fallback += f"{i}. {source.source_id}\n"
        
        fallback += "\n**Recommendation**: Please consult these sources directly or speak with a healthcare professional "
        fallback += "for accurate information.\n\n"
        fallback += "⚠️ **Medical Disclaimer**: This tool is for educational purposes only and does not provide medical advice. "
        fallback += "Always consult qualified healthcare professionals for medical decisions."
        
        return fallback
    
    async def process(
        self,
        query: str,
        initial_answer: str,
        sources: List[Source],
        regenerate_fn: Optional[Callable] = None,
        max_retries: int = 2
    ) -> Dict:
        """
        完整的评估和决策流程
        
        Args:
            query: 用户问题
            initial_answer: 初始生成的答案
            sources: 参考来源
            regenerate_fn: 重新生成答案的函数
            max_retries: 最大重试次数
            
        Returns:
            最终答案和评估结果
        """
        current_answer = initial_answer
        retry_count = 0
        
        while retry_count <= max_retries:
            # 评估当前答案
            evaluation = await self.evaluate(query, current_answer, sources)
            score = evaluation["weighted_score"]
            quality = evaluation["quality_level"]
            
            # 高质量：直接使用
            if quality == "high":
                print(f"✅ High quality answer approved (score: {score:.1f})")
                return {
                    "answer": current_answer,
                    "status": "approved",
                    "evaluation": evaluation,
                    "retry_count": retry_count
                }
            
            # 中等质量：添加警告
            elif quality == "medium":
                print(f"⚠️ Medium quality answer (score: {score:.1f}), adding warning")
                warning = self._build_warning(evaluation)
                return {
                    "answer": current_answer + warning,
                    "status": "approved_with_warning",
                    "evaluation": evaluation,
                    "retry_count": retry_count
                }
            
            # 低质量：重新生成
            else:
                print(f"❌ Low quality (score: {score:.1f})")
                
                # 检查是否还有重试机会
                if retry_count >= max_retries:
                    print(f"🔄 Max retries reached, using fallback")
                    fallback = self._build_fallback(query, sources)
                    return {
                        "answer": fallback,
                        "status": "fallback",
                        "evaluation": evaluation,
                        "retry_count": retry_count
                    }
                
                # 如果没有重新生成函数，使用后备
                if not regenerate_fn:
                    print(f"⚠️ No regenerate function provided, using fallback")
                    fallback = self._build_fallback(query, sources)
                    return {
                        "answer": fallback,
                        "status": "fallback",
                        "evaluation": evaluation,
                        "retry_count": retry_count
                    }
                
                # 重新生成
                print(f"🔄 Regenerating answer (attempt {retry_count + 1}/{max_retries})")
                
                # 构建反馈
                feedback = "Previous answer issues:\n"
                for issue in evaluation.get("issues", []):
                    feedback += f"- {issue}\n"
                feedback += "\nRecommendations:\n"
                for rec in evaluation.get("recommendations", []):
                    feedback += f"- {rec}\n"
                
                # 重新生成答案
                try:
                    current_answer = await regenerate_fn(query, sources, feedback)
                    retry_count += 1
                except Exception as e:
                    print(f"❌ Regeneration failed: {e}")
                    fallback = self._build_fallback(query, sources)
                    return {
                        "answer": fallback,
                        "status": "fallback",
                        "evaluation": evaluation,
                        "retry_count": retry_count
                    }


# 创建全局 LLM Judge 实例
llm_judge = LLMJudge()


# 测试代码（仅在直接运行此文件时执行）
if __name__ == "__main__":
    async def test_llm_judge():
        """测试 LLM Judge 功能"""
        
        # 测试数据
        query = "What are the side effects of Metformin?"
        
        # 好的答案
        good_answer = """
        Metformin commonly causes the following side effects:
        - Diarrhea (most common, ~53% of patients)
        - Nausea and vomiting (~26%)
        - Abdominal discomfort
        - Indigestion
        
        Rare but serious: Lactic acidosis (very rare but potentially fatal)
        
        **Medical Disclaimer**: This information is for educational purposes only. 
        Please consult a qualified healthcare professional for personalized medical advice.
        """
        
        # 差的答案（包含编造内容）
        bad_answer = """
        Metformin side effects include:
        - Severe liver damage (15% of patients)
        - Heart arrhythmia (20% of patients)
        - Memory loss
        - All side effects are reversible upon stopping the drug
        """
        
        # 模拟来源
        sources = [
            Source(
                source_id="FDA-Metformin",
                content="""
                Metformin most common adverse reactions include:
                - Diarrhea (incidence ~53%)
                - Nausea/vomiting (incidence ~26%)
                - Abdominal discomfort (incidence ~9%)
                - Indigestion (incidence ~7%)
                
                Rare but serious: Lactic acidosis (very rare but can be fatal)
                """
            )
        ]
        
        # 测试好的答案
        print("\n" + "="*60)
        print("=== Test 1: Good Answer ===")
        print("="*60)
        evaluation1 = await llm_judge.evaluate(query, good_answer, sources)
        print(f"\nScores: {evaluation1['scores']}")
        print(f"Weighted Score: {evaluation1['weighted_score']}")
        print(f"Quality Level: {evaluation1['quality_level']}")
        
        # 测试差的答案
        print("\n" + "="*60)
        print("=== Test 2: Bad Answer ===")
        print("="*60)
        evaluation2 = await llm_judge.evaluate(query, bad_answer, sources)
        print(f"\nScores: {evaluation2['scores']}")
        print(f"Weighted Score: {evaluation2['weighted_score']}")
        print(f"Quality Level: {evaluation2['quality_level']}")
        print(f"Issues: {evaluation2.get('issues', [])}")
        
        # 测试完整流程
        print("\n" + "="*60)
        print("=== Test 3: Full Process with Bad Answer ===")
        print("="*60)
        
        async def mock_regenerate(q, s, feedback):
            """模拟重新生成函数"""
            print(f"\n📝 Regenerating with feedback:\n{feedback[:200]}...")
            return good_answer  # 返回好的答案
        
        result = await llm_judge.process(
            query=query,
            initial_answer=bad_answer,
            sources=sources,
            regenerate_fn=mock_regenerate,
            max_retries=2
        )
        
        print(f"\nFinal Status: {result['status']}")
        print(f"Retry Count: {result['retry_count']}")
        print(f"Final Score: {result['evaluation']['weighted_score']}")
    
    # 运行测试
    asyncio.run(test_llm_judge())