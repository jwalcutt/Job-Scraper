"""
Extract text from uploaded resume files (PDF and DOCX).
Optionally uses spaCy NER to suggest skills and titles.
"""
import io
from typing import Optional


def extract_text_from_pdf(content: bytes) -> str:
    from pdfminer.high_level import extract_text as pdfminer_extract
    return pdfminer_extract(io.BytesIO(content)).strip()


def extract_text_from_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_skills_and_titles(text: str) -> dict[str, list[str]]:
    """
    Use spaCy NER to pull candidate skills and job titles from resume text.
    Returns suggestions; the user can accept/edit them in the frontend.
    """
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(text[:10_000])  # cap to avoid timeout on huge resumes

    titles: list[str] = []
    skills: list[str] = []

    for ent in doc.ents:
        if ent.label_ in ("ORG", "PERSON"):
            continue
        if ent.label_ == "WORK_OF_ART":
            skills.append(ent.text)

    # Simple heuristic: NOUN chunks that look like tech skills
    common_skills_keywords = {
        "python", "javascript", "typescript", "react", "node", "aws", "gcp", "azure",
        "docker", "kubernetes", "sql", "postgresql", "redis", "graphql", "rest", "api",
        "machine learning", "deep learning", "tensorflow", "pytorch", "spark", "kafka",
        "java", "go", "rust", "c++", "c#", ".net", "ruby", "rails", "django", "fastapi",
        "flask", "spring", "git", "ci/cd", "agile", "scrum",
    }
    lower_text = text.lower()
    skills = [kw for kw in common_skills_keywords if kw in lower_text]

    return {"skills": sorted(set(skills)), "suggested_titles": titles}
