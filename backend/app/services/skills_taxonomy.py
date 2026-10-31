"""A dictionary of known skills and a matcher.

Format:  "Canonical Name": ["alias one", "alias two", ...]
Matching ignores upper/lower case, except for names in CASE_SENSITIVE_SKILLS
(English words like "react" or "ruby" would otherwise match normal sentences).
Skills that are single letters or ordinary words (C, R, Go) are NOT included on purpose.
You can add your own skills here at any time.
"""

import re

SKILL_ALIASES: dict[str, list[str]] = {
    # Languages
    "Python": ["python"],
    "JavaScript": ["javascript"],
    "TypeScript": ["typescript"],
    "Java": ["java"],
    "C++": ["c++"],
    "C#": ["c#"],
    "PHP": ["php"],
    "Ruby": ["Ruby"],
    "Kotlin": ["kotlin"],
    "Swift": ["Swift"],
    "Rust": ["Rust"],
    "Scala": ["scala"],
    "Bash": ["bash", "shell scripting"],
    # Web / frontend
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "React": ["React", "React.js", "ReactJS", "ReactJs"],
    "Next.js": ["next.js", "nextjs"],
    "Angular": ["angular", "angularjs"],
    "Vue.js": ["vue", "vue.js", "vuejs"],
    "Tailwind CSS": ["tailwind css", "tailwindcss", "tailwind"],
    "Redux": ["redux"],
    # Backend
    "Node.js": ["node.js", "nodejs", "node js"],
    "Express.js": ["express.js", "expressjs"],
    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Django": ["django"],
    "Spring Boot": ["spring boot", "springboot"],
    ".NET": ["asp.net core", "asp.net", ".net", "dotnet"],
    "REST APIs": ["rest apis", "rest api", "restful apis", "restful api", "restful"],
    "GraphQL": ["graphql"],
    "Microservices": ["microservices", "microservice"],
    # Databases
    "SQL": ["sql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MySQL": ["mysql"],
    "SQLite": ["sqlite"],
    "MongoDB": ["mongodb"],
    "Redis": ["redis"],
    "NoSQL": ["nosql"],
    "Elasticsearch": ["elasticsearch"],
    # DevOps / cloud
    "Git": ["git"],
    "GitHub": ["github"],
    "GitHub Actions": ["github actions"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "CI/CD": ["ci/cd", "cicd"],
    "Jenkins": ["jenkins"],
    "Linux": ["linux"],
    "AWS": ["aws", "amazon web services"],
    "Azure": ["azure"],
    "Google Cloud": ["google cloud platform", "google cloud", "gcp"],
    "Terraform": ["terraform"],
    "Nginx": ["nginx"],
    # Testing
    "Unit Testing": ["unit testing", "unit tests", "unit test"],
    "pytest": ["pytest"],
    "Jest": ["jest"],
    "Selenium": ["selenium"],
    "Postman": ["postman"],
    # Data / AI
    "Machine Learning": ["machine learning"],
    "Deep Learning": ["deep learning"],
    "NLP": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "LangChain": ["langchain"],
    "LangGraph": ["langgraph"],
    "LLMs": ["large language models", "llms", "llm"],
    "Generative AI": ["generative ai", "genai"],
    "Prompt Engineering": ["prompt engineering"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Data Analysis": ["data analysis", "data analytics"],
    "Data Structures": ["data structures"],
    # Practices
    "Agile": ["agile"],
    "Scrum": ["scrum"],
    "Object-Oriented Programming": [
        "object-oriented programming",
        "object oriented programming",
        "oop",
    ],
}

CASE_SENSITIVE_SKILLS = {"React", "Ruby", "Swift", "Rust"}


def _compile(name: str, aliases: list[str]) -> re.Pattern[str]:
    # Longest aliases first, so "rest apis" is tried before "rest".
    body = "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True))
    flags = 0 if name in CASE_SENSITIVE_SKILLS else re.IGNORECASE
    # The skill must not be glued to other letters/digits, so "Java" does not match
    # inside "JavaScript" and "SQL" does not match inside "PostgreSQL".
    return re.compile(r"(?<![A-Za-z0-9+#])(?:" + body + r")(?![A-Za-z0-9+#])", flags)


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (name, _compile(name, aliases)) for name, aliases in SKILL_ALIASES.items()
]


def find_skills(text: str) -> list[tuple[str, str]]:
    """Return [(canonical_name, text_as_written)] for each skill found, in order of appearance."""
    hits: list[tuple[int, str, str]] = []
    for name, pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            hits.append((match.start(), name, match.group(0)))
    hits.sort()
    return [(name, matched) for _, name, matched in hits]