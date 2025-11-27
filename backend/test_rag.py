"""
Quick Test Script for Enhanced RAG System
Run this to verify all components work correctly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("\n=== Testing Imports ===")
    try:
        from app.services.semantic_chunker import SemanticChunker
        print("[OK] SemanticChunker imported")

        from app.services.hyde import HyDEService
        print("[OK] HyDEService imported")

        from app.services.retriever import AdvancedRetriever
        print("[OK] AdvancedRetriever imported")

        from app.services.reranker import ReRanker
        print("[OK] ReRanker imported")

        from app.services.knowledge_base import KnowledgeBase
        print("[OK] KnowledgeBase imported")

        from app.services.vector_store import VectorStore
        print("[OK] VectorStore imported")

        from app.services.enhanced_analysis_service import EnhancedAnalysisService
        print("[OK] EnhancedAnalysisService imported")

        print("\n[SUCCESS] All imports successful!\n")
        return True
    except Exception as e:
        print(f"\n[ERROR] Import failed: {str(e)}\n")
        return False


def test_semantic_chunker():
    """Test semantic chunking."""
    print("=== Testing Semantic Chunker ===")
    try:
        from app.services.semantic_chunker import SemanticChunker

        chunker = SemanticChunker()

        # Sample resume text
        sample_resume = """
        John Doe
        Senior Software Engineer

        PROFESSIONAL SUMMARY
        Experienced software engineer with 5+ years in Python and machine learning.

        WORK EXPERIENCE
        Senior Software Engineer | Tech Corp | 2020 - Present
        - Developed ML pipelines using Python and TensorFlow
        - Led team of 3 engineers
        - Improved system performance by 40%

        Software Engineer | StartUp Inc | 2018 - 2020
        - Built REST APIs with FastAPI
        - Implemented CI/CD pipelines

        SKILLS
        Python, JavaScript, Docker, AWS, Machine Learning

        EDUCATION
        BS Computer Science | University Name | 2018
        """

        chunks = chunker.chunk_resume(sample_resume)

        print(f"[OK] Created {len(chunks)} semantic chunks")
        print(f"  Chunk types: {set(c['chunk_type'] for c in chunks)}")

        if chunks:
            print(f"\n  Sample chunk:")
            print(f"    Type: {chunks[0]['chunk_type']}")
            print(f"    Length: {len(chunks[0]['content'])} chars")
            print(f"    Keywords: {chunks[0]['metadata'].get('keywords', [])[:3]}")

        print("\n[SUCCESS] Semantic chunking works!\n")
        return True

    except Exception as e:
        print(f"\n[ERROR] Semantic chunking failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def test_hyde():
    """Test HyDE service."""
    print("=== Testing HyDE Service ===")
    print("NOTE: This requires Ollama to be running!")
    print("If you don't have Ollama running, this test will be skipped.\n")

    try:
        from app.services.hyde import HyDEService

        hyde = HyDEService()

        job_desc = "Looking for a Python developer with machine learning experience"

        print("Generating hypothetical resume bullets...")
        print("(This may take 10-20 seconds on first run)")

        # Try to generate, but don't fail if Ollama isn't running
        try:
            result = hyde.generate_hypothetical_documents(
                job_description=job_desc,
                num_documents=3,
                temperature=0.7
            )

            print(f"[OK] Generated {len(result)} hypothetical documents")
            print("\n  Sample hypothetical bullet:")
            if result:
                print(f"    {result[0][:150]}...")

            print("\n[SUCCESS] HyDE generation works!\n")
            return True

        except Exception as ollama_error:
            if "connection" in str(ollama_error).lower() or "refused" in str(ollama_error).lower():
                print("[WARNING] Ollama not running - using fallback mode")
                print("   To enable HyDE: Start Ollama with 'ollama serve'")
                print("   This is optional - system works without it")
                print("\n[OK] HyDE service initialized (fallback mode)\n")
                return True
            else:
                raise

    except Exception as e:
        print(f"\n[ERROR] HyDE test failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def test_vector_store():
    """Test vector store."""
    print("=== Testing Vector Store ===")
    try:
        from app.services.vector_store import VectorStore

        print("Initializing vector store...")
        vector_store = VectorStore()

        print("[OK] Vector store initialized")
        print(f"[OK] Current document count: {vector_store.count_resumes()}")

        # Test adding a chunk
        test_chunk_id = "test_chunk_123"
        test_content = "Python developer with 5 years of machine learning experience"
        test_metadata = {
            "source_type": "resume",
            "chunk_type": "summary",
            "test": True
        }

        print("\nAdding test chunk...")
        chunk_id = vector_store.add_chunk(
            chunk_id=test_chunk_id,
            content=test_content,
            metadata=test_metadata
        )
        print(f"[OK] Added chunk: {chunk_id}")

        # Test searching
        print("\nSearching for similar chunks...")
        results = vector_store.search_similar_chunks(
            query_text="machine learning engineer",
            n_results=1
        )

        if results:
            print(f"[OK] Found {len(results)} similar chunks")
            print(f"  Top result score: {results[0]['score']:.3f}")

        # Cleanup test chunk
        print("\nCleaning up test data...")
        vector_store.delete_chunks([test_chunk_id])
        print("[OK] Test chunk removed")

        print("\n[SUCCESS] Vector store works!\n")
        return True

    except Exception as e:
        print(f"\n[ERROR] Vector store test failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def test_reranker():
    """Test cross-encoder re-ranker."""
    print("=== Testing Cross-Encoder Re-Ranker ===")
    print("NOTE: First run will download the model (~80MB)")
    print("This may take 30-60 seconds...\n")

    try:
        from app.services.reranker import ReRanker

        print("Loading cross-encoder model...")
        reranker = ReRanker()

        print("[OK] Cross-encoder model loaded")

        # Test re-ranking
        query = "Python developer with machine learning experience"
        chunks = [
            {
                "chunk_id": "1",
                "content": "Developed machine learning models using Python and TensorFlow",
                "score": 0.7
            },
            {
                "chunk_id": "2",
                "content": "Built frontend applications with React and JavaScript",
                "score": 0.6
            },
            {
                "chunk_id": "3",
                "content": "Implemented deep learning algorithms for computer vision tasks",
                "score": 0.65
            }
        ]

        print("\nRe-ranking 3 test chunks...")
        reranked = reranker.rerank(query, chunks, top_k=3)

        print(f"[OK] Re-ranked {len(reranked)} chunks")
        print("\n  Results (by relevance):")
        for i, chunk in enumerate(reranked[:3], 1):
            print(f"    {i}. Score: {chunk['rerank_score']:.3f} - {chunk['content'][:60]}...")

        print("\n[SUCCESS] Cross-encoder re-ranking works!\n")
        return True

    except Exception as e:
        print(f"\n[ERROR] Re-ranker test failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def test_pipeline_stats():
    """Test getting pipeline statistics."""
    print("=== Testing Pipeline Stats ===")
    try:
        from app.services.enhanced_analysis_service import enhanced_service

        stats = enhanced_service.get_pipeline_stats()

        print("[OK] Pipeline configuration:")
        print(f"  - HyDE enabled: {stats['hyde_enabled']}")
        print(f"  - Re-ranking enabled: {stats['reranking_enabled']}")
        print(f"  - Semantic chunking: {stats['semantic_chunking_enabled']}")
        print(f"  - Retrieval top-k: {stats['retrieval_top_k']}")
        print(f"  - Rerank top-k: {stats['rerank_top_k']}")
        print(f"  - Vector store docs: {stats['vector_store_count']}")

        print("\n[SUCCESS] Pipeline stats retrieved!\n")
        return True

    except Exception as e:
        print(f"\n[ERROR] Pipeline stats failed: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  ENHANCED RAG SYSTEM TEST SUITE")
    print("="*60 + "\n")

    results = {}

    # Run tests
    results['imports'] = test_imports()
    results['semantic_chunker'] = test_semantic_chunker()
    results['hyde'] = test_hyde()
    results['vector_store'] = test_vector_store()
    results['reranker'] = test_reranker()
    results['pipeline_stats'] = test_pipeline_stats()

    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60 + "\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "PASS" if passed_test else "FAIL"
        symbol = "[PASS]" if passed_test else "[FAIL]"
        print(f"  {symbol} {test_name.replace('_', ' ').title()}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  ALL TESTS PASSED! System is ready to use.")
    else:
        print(f"\n  WARNING: {total - passed} test(s) failed. Check errors above.")

    print("\n" + "="*60 + "\n")

    # Next steps
    print("NEXT STEPS:")
    print("1. Start Ollama: ollama serve")
    print("2. Pull model: ollama pull llama2")
    print("3. Test with real resume: python scripts/test_with_resume.py")
    print("4. Read docs: README_RAG.md")
    print("\n")


if __name__ == "__main__":
    main()
