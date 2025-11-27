"""
Quick test script for enhanced RAG analysis
Usage: python quick_test.py
"""

from app.services.enhanced_analysis_service import enhanced_service

# Sample job description
job_description = """
We are looking for a Senior Software Engineer with the following qualifications:

Required Skills:
- 5+ years of Python development experience
- Strong experience with machine learning frameworks (TensorFlow, PyTorch)
- Experience with REST APIs and microservices architecture
- Proficiency with Docker and AWS
- Strong problem-solving and communication skills

Responsibilities:
- Design and develop machine learning pipelines
- Build scalable backend services with FastAPI
- Collaborate with data scientists and product teams
- Mentor junior engineers
- Lead technical design discussions

Nice to Have:
- Experience with NLP and transformers
- Knowledge of vector databases (ChromaDB, Pinecone)
- CI/CD pipeline experience
- Open source contributions
"""

# Option 1: Test with a sample resume (create one on the fly)
sample_resume_text = """
JOHN DOE
Senior Software Engineer
john.doe@email.com | (555) 123-4567 | linkedin.com/in/johndoe

PROFESSIONAL SUMMARY
Experienced software engineer with 6+ years specializing in Python development and machine learning.
Proven track record of building scalable systems and leading technical teams.

WORK EXPERIENCE

Senior Software Engineer | Tech Corp | 2020 - Present
- Developed ML pipelines processing 1M+ records daily using Python and TensorFlow
- Built REST APIs with FastAPI serving 10K requests/minute
- Led team of 3 engineers in microservices migration
- Improved system performance by 40% through optimization
- Deployed services on AWS using Docker and Kubernetes

Software Engineer | StartUp Inc | 2018 - 2020
- Built NLP models for text classification with 92% accuracy
- Implemented CI/CD pipelines reducing deployment time by 60%
- Developed real-time data processing systems
- Mentored 2 junior developers

SKILLS
Python, TensorFlow, PyTorch, FastAPI, Docker, AWS, Kubernetes, PostgreSQL,
REST APIs, Machine Learning, NLP, Git, CI/CD, Agile

EDUCATION
BS Computer Science | University Name | 2018
GPA: 3.8/4.0

PROJECTS
- Built open-source Python library for data processing (500+ GitHub stars)
- Contributed to TensorFlow documentation
"""

print("\n" + "="*70)
print("  TESTING ENHANCED RAG SYSTEM")
print("="*70 + "\n")

# Save sample resume to a temporary file
import tempfile
import os

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write(sample_resume_text)
    temp_resume_path = f.name

try:
    print("Analyzing resume with enhanced RAG pipeline...")
    print("(This may take 5-10 seconds for the full pipeline)\n")

    # Run the enhanced analysis
    result = enhanced_service.analyze_resume_enhanced(
        resume_path=temp_resume_path,
        job_description=job_description,
        job_title="Senior Software Engineer",
        enable_evaluation=False  # Set to True to test evaluation
    )

    # Display results
    print("\n" + "="*70)
    print("  ANALYSIS RESULTS")
    print("="*70 + "\n")

    # Match Score
    match_score = result['match_analysis']['overall_score']
    print(f"Overall Match Score: {match_score}/100")
    print(f"Rating: {result['match_analysis']['match_level']}\n")

    # Matched Skills
    matched = result['match_analysis']['matched_skills']
    print(f"Matched Skills ({len(matched)}):")
    for skill in matched[:10]:  # Show first 10
        print(f"  - {skill}")
    if len(matched) > 10:
        print(f"  ... and {len(matched) - 10} more\n")
    else:
        print()

    # Missing Skills
    missing = result['match_analysis']['missing_skills']
    if missing:
        print(f"Missing Skills ({len(missing)}):")
        for skill in missing[:5]:  # Show first 5
            print(f"  - {skill}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more\n")
        else:
            print()

    # RAG Pipeline Performance
    print("\n" + "-"*70)
    print("  RAG PIPELINE STATS")
    print("-"*70 + "\n")

    metadata = result['rag_metadata']
    print(f"Total Duration: {metadata['total_duration']:.2f}s")
    print(f"Chunks Retrieved: {metadata['chunks_retrieved']}")
    print(f"HyDE Used: {'Yes' if metadata.get('hyde_used') else 'No'}")
    print(f"Re-ranking Used: {'Yes' if metadata.get('reranking_used') else 'No'}")

    # Show top retrieved chunks
    if 'retrieved_chunks' in result:
        print(f"\nTop 3 Retrieved Resume Sections:")
        for i, chunk in enumerate(result['retrieved_chunks'][:3], 1):
            print(f"\n  {i}. Type: {chunk.get('chunk_type', 'unknown')} | Score: {chunk.get('score', 0):.3f}")
            content = chunk['content'][:150] + "..." if len(chunk['content']) > 150 else chunk['content']
            print(f"     {content}")

    # Improvements
    if result.get('improvements'):
        print("\n" + "-"*70)
        print("  SUGGESTED IMPROVEMENTS")
        print("-"*70 + "\n")
        for improvement in result['improvements'][:3]:
            print(f"  - {improvement}")

    print("\n" + "="*70)
    print("  TEST COMPLETED SUCCESSFULLY!")
    print("="*70 + "\n")

finally:
    # Cleanup temp file
    if os.path.exists(temp_resume_path):
        os.unlink(temp_resume_path)

print("\nNext Steps:")
print("1. Test with your own resume: Update temp_resume_path with your PDF/TXT file")
print("2. Try different job descriptions")
print("3. Enable evaluation: set enable_evaluation=True")
print("4. Test the API server: python main.py")
print("5. Run benchmarks: python scripts/benchmark.py --quick\n")
