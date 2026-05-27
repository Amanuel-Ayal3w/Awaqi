"""
Advanced RAGAS usage examples for the Awaqi RAG system.

Shows how to:
- Run evaluation on specific test cases
- Create custom test datasets
- Compare different RAG configurations
- Integrate with CI/CD pipelines
"""

import asyncio
from ai_engine.evaluation import evaluate_rag


# Example 1: Quick evaluation on custom data
async def example_quick_evaluation():
    """Evaluate a few questions/answers."""
    print("\n=== Example 1: Quick Evaluation ===")
    
    questions = [
        "What is income tax?",
        "How do I file a tax return?",
    ]
    
    answers = [
        "Income tax is a tax levied on the earnings of individuals.",
        "You can file your tax return online through the government portal.",
    ]
    
    contexts = [
        [
            "Income tax is a direct tax on the earnings of individuals from employment, business, and other sources.",
            "The tax rate depends on income brackets set by the Ethiopian Revenue Authority.",
        ],
        [
            "Tax returns can be filed online through the official government portal.",
            "The filing deadline is typically at the end of the fiscal year.",
        ],
    ]
    
    results = await evaluate_rag(
        questions=questions,
        answers=answers,
        contexts=contexts,
    )
    
    print(f"Faithfulness:      {results.faithfulness_score:.4f}")
    print(f"Answer Relevancy:  {results.answer_relevancy_score:.4f}")
    print(f"Context Recall:    {results.context_recall_score:.4f}")
    print(f"Context Precision: {results.context_precision_score:.4f}")
    print(f"Average:           {results.average_score:.4f}")


# Example 2: A/B Testing - Compare two RAG configurations
async def example_ab_test():
    """Compare baseline vs improved RAG configuration."""
    print("\n=== Example 2: A/B Testing ===")
    
    questions = ["What is VAT?", "What deductions are allowed?"]
    contexts_v1 = [
        ["VAT is a type of sales tax."],
        ["Various deductions may apply."],
    ]
    contexts_v2 = [
        [
            "VAT (Value Added Tax) is a consumption tax applied at each stage of the supply chain.",
            "VAT is calculated as a percentage of the sale price.",
            "VAT applies to most goods and services in the economy.",
        ],
        [
            "Professional expenses are tax-deductible.",
            "Insurance premiums can be deducted from taxable income.",
            "Charitable contributions may be deductible.",
        ],
    ]
    
    # Baseline answers (simple)
    answers_v1 = [
        "VAT is a tax.",
        "Some deductions exist.",
    ]
    
    # Improved answers (detailed)
    answers_v2 = [
        "VAT is a consumption tax calculated at each stage of the supply chain, applied as a percentage of the sale price.",
        "Professional expenses, insurance premiums, and charitable contributions are commonly deductible.",
    ]
    
    print("Baseline (v1):")
    baseline = await evaluate_rag(
        questions=questions,
        answers=answers_v1,
        contexts=contexts_v1,
    )
    print(f"  Average Score: {baseline.average_score:.4f}")
    
    print("\nImproved (v2):")
    improved = await evaluate_rag(
        questions=questions,
        answers=answers_v2,
        contexts=contexts_v2,
    )
    print(f"  Average Score: {improved.average_score:.4f}")
    
    improvement = improved.average_score - baseline.average_score
    print(f"\nImprovement: {improvement:+.4f} ({improvement*100:+.2f}%)")


# Example 3: Threshold-based validation (for CI/CD)
async def example_ci_validation():
    """Check if RAG system meets quality thresholds."""
    print("\n=== Example 3: CI/CD Validation ===")
    
    questions = ["How do I pay taxes?", "What is the tax deadline?"]
    answers = ["Taxes can be paid online.", "The deadline is end of year."]
    contexts = [
        ["Online payment is available on the government website."],
        ["Tax returns must be filed by December 31st."],
    ]
    
    results = await evaluate_rag(
        questions=questions,
        answers=answers,
        contexts=contexts,
    )
    
    # Define thresholds
    thresholds = {
        "faithfulness": 0.75,
        "answer_relevancy": 0.75,
        "context_recall": 0.70,
        "context_precision": 0.75,
        "overall": 0.73,
    }
    
    passed = True
    
    print("Quality Checks:")
    if results.faithfulness_score < thresholds["faithfulness"]:
        print(f"❌ Faithfulness {results.faithfulness_score:.4f} < {thresholds['faithfulness']}")
        passed = False
    else:
        print(f"✓ Faithfulness {results.faithfulness_score:.4f} >= {thresholds['faithfulness']}")
    
    if results.answer_relevancy_score < thresholds["answer_relevancy"]:
        print(f"❌ Answer Relevancy {results.answer_relevancy_score:.4f} < {thresholds['answer_relevancy']}")
        passed = False
    else:
        print(f"✓ Answer Relevancy {results.answer_relevancy_score:.4f} >= {thresholds['answer_relevancy']}")
    
    if results.context_precision_score < thresholds["context_precision"]:
        print(f"❌ Context Precision {results.context_precision_score:.4f} < {thresholds['context_precision']}")
        passed = False
    else:
        print(f"✓ Context Precision {results.context_precision_score:.4f} >= {thresholds['context_precision']}")
    
    if results.average_score < thresholds["overall"]:
        print(f"❌ Overall {results.average_score:.4f} < {thresholds['overall']}")
        passed = False
    else:
        print(f"✓ Overall {results.average_score:.4f} >= {thresholds['overall']}")
    
    if passed:
        print("\n✅ All checks passed! Ready to deploy.")
        return 0
    else:
        print("\n❌ Deployment blocked. Fix quality issues first.")
        return 1


# Example 4: Evaluation with ground truths (for context recall)
async def example_with_ground_truth():
    """Evaluate with expected answers for context recall."""
    print("\n=== Example 4: Evaluation with Ground Truths ===")
    
    questions = [
        "What is income tax?",
        "What deductions can I claim?",
    ]
    
    answers = [
        "Income tax is levied on earnings.",
        "You can claim professional expenses.",
    ]
    
    contexts = [
        [
            "Income tax is a direct tax on earnings from employment and business.",
        ],
        [
            "Professional expenses, insurance, and charitable donations are deductible.",
        ],
    ]
    
    ground_truths = [
        "Income tax is a government levy on earnings of individuals.",
        "Common deductions include professional expenses, insurance premiums, and charitable contributions.",
    ]
    
    results = await evaluate_rag(
        questions=questions,
        answers=answers,
        contexts=contexts,
        ground_truths=ground_truths,
    )
    
    print(f"With ground truths:")
    print(f"  Faithfulness:      {results.faithfulness_score:.4f}")
    print(f"  Answer Relevancy:  {results.answer_relevancy_score:.4f}")
    print(f"  Context Recall:    {results.context_recall_score:.4f} ← requires ground_truth")
    print(f"  Context Precision: {results.context_precision_score:.4f}")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("RAGAS Advanced Examples")
    print("=" * 60)
    
    await example_quick_evaluation()
    await example_ab_test()
    exit_code = await example_ci_validation()
    await example_with_ground_truth()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    
    return exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
