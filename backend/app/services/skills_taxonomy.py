"""Comprehensive skills taxonomy with normalization and similarity scoring."""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Skills database organized by category
# ---------------------------------------------------------------------------

SKILLS_TAXONOMY: dict[str, dict[str, list[str]]] = {
    "programming": {
        "python": ["python", "python3", "python3.x", "py"],
        "java": ["java", "java8", "java11", "java17", "java21", "j2ee", "j2se"],
        "javascript": ["javascript", "js", "es6", "es2015", "ecmascript"],
        "typescript": ["typescript", "ts"],
        "c#": ["c#", "csharp", "c sharp", ".net", ".net core"],
        "c++": ["c++", "cpp", "c plus plus"],
        "go": ["go", "golang"],
        "rust": ["rust", "rustlang"],
        "ruby": ["ruby", "ruby on rails", "rails"],
        "php": ["php", "php8", "laravel", "symfony"],
        "kotlin": ["kotlin", "kt"],
        "swift": ["swift", "swiftui"],
        "scala": ["scala", "spark scala"],
        "r": ["r", "r programming", "r language"],
        "sql": ["sql", "mysql", "postgresql", "plsql", "tsql"],
        "shell scripting": ["bash", "shell", "zsh", "powershell", "shell scripting"],
        "perl": ["perl"],
        "dart": ["dart", "flutter dart"],
        "elixir": ["elixir", "erlang"],
        "lua": ["lua"],
    },
    "frontend": {
        "react": ["react", "reactjs", "react.js", "react18"],
        "angular": ["angular", "angularjs", "angular2+", "angular 2+", "ng"],
        "vue": ["vue", "vuejs", "vue.js", "vue3", "vue 3"],
        "next.js": ["next.js", "nextjs", "next"],
        "svelte": ["svelte", "sveltekit"],
        "html": ["html", "html5"],
        "css": ["css", "css3", "scss", "sass", "less", "tailwind css", "tailwind", "bootstrap", "material ui", "chakra ui"],
        "redux": ["redux", "mobx", "zustand", "recoil", "jotai"],
        "graphql": ["graphql", "apollo client", "relay"],
        "webpack": ["webpack", "vite", "rollup", "esbuild"],
        "figma": ["figma", "adobe xd", "sketch", "invision"],
    },
    "backend_frameworks": {
        "spring boot": ["spring boot", "spring", "spring mvc", "spring security", "spring cloud"],
        "django": ["django", "django rest framework", "drf"],
        "flask": ["flask"],
        "fastapi": ["fastapi", "fast api"],
        "express": ["express", "expressjs", "express.js"],
        "node.js": ["node.js", "nodejs", "node"],
        "ruby on rails": ["rails", "ruby on rails"],
        "laravel": ["laravel"],
        "asp.net": ["asp.net", "asp.net core", "aspnet", "blazor"],
        "nest.js": ["nestjs", "nest.js"],
        "hibernate": ["hibernate", "jpa"],
        "microservices": ["microservices", "microservices architecture", "distributed systems"],
        "rest api": ["rest api", "restful", "rest", "rest apis"],
        "soap": ["soap", "web services"],
        "grpc": ["grpc", "protobuf"],
    },
    "data": {
        "postgresql": ["postgresql", "postgres", "psql"],
        "mysql": ["mysql", "mariadb"],
        "mongodb": ["mongodb", "mongo", "nosql"],
        "redis": ["redis", "cache", "memcached"],
        "oracle": ["oracle", "oracle db", "plsql"],
        "snowflake": ["snowflake", "snowflake db"],
        "databricks": ["databricks"],
        "bigquery": ["bigquery", "google bigquery"],
        "redshift": ["redshift", "aws redshift"],
        "elasticsearch": ["elasticsearch", "elastic", "opensearch", "kibana"],
        "neo4j": ["neo4j", "graph database"],
        "cassandra": ["cassandra", "cassandra db"],
        "couchdb": ["couchdb", "couchbase"],
        "dynamodb": ["dynamodb", "dynamo"],
        "firebase": ["firebase", "firebase realtime"],
    },
    "data_engineering": {
        "spark": ["spark", "pyspark", "apache spark"],
        "hadoop": ["hadoop", "hdfs", "mapreduce"],
        "kafka": ["kafka", "apache kafka", "confluent"],
        "airflow": ["airflow", "apache airflow", "dag"],
        "dbt": ["dbt"],
        "etl": ["etl", "data pipeline", "data pipelines"],
        "tableau": ["tableau"],
        "power bi": ["power bi", "powerbi"],
        "looker": ["looker", "lookml"],
        "data warehouse": ["data warehouse", "data warehousing", "snowflake"],
        "data lake": ["data lake", "datalake", "lakehouse"],
        "glue": ["aws glue", "glue"],
        "dataflow": ["dataflow", "google dataflow", "apache beam"],
        "flink": ["flink", "apache flink"],
        "storm": ["storm", "apache storm"],
        "luigi": ["luigi"],
        "prefect": ["prefect"],
        "dagster": ["dagster"],
        "mage": ["mage", "mage ai"],
    },
    "ai_ml": {
        "machine learning": ["machine learning", "ml", "statistical learning"],
        "deep learning": ["deep learning", "dl", "neural networks"],
        "nlp": ["nlp", "natural language processing", "text mining"],
        "computer vision": ["computer vision", "cv", "image processing", "object detection"],
        "pytorch": ["pytorch", "torch"],
        "tensorflow": ["tensorflow", "tf", "keras"],
        "scikit-learn": ["scikit-learn", "sklearn"],
        "pandas": ["pandas", "pd"],
        "numpy": ["numpy", "np"],
        "llm": ["llm", "large language model", "large language models"],
        "genai": ["genai", "generative ai", "generative ai"],
        "langchain": ["langchain", "lang chain"],
        "rag": ["rag", "retrieval augmented generation"],
        "openai": ["openai", "gpt", "gpt-4", "gpt-3.5", "chatgpt", "chatgpt api"],
        "prompt engineering": ["prompt engineering", "prompting", "prompt design"],
        "transformers": ["transformers", "bert", "gpt", "attention mechanism"],
        "hugging face": ["huggingface", "hugging face", "hf"],
        "xgboost": ["xgboost", "lightgbm", "catboost"],
        "time series": ["time series", "forecasting", "prophet"],
        "recommendation systems": ["recommendation systems", "collaborative filtering"],
        "mlops": ["mlops", "ml ops", "machine learning operations"],
        "mlflow": ["mlflow", "ml flow"],
        "kubeflow": ["kubeflow"],
        "h2o": ["h2o", "h2o.ai"],
    },
    "cloud": {
        "aws": ["aws", "amazon web services", "amazon aws"],
        "azure": ["azure", "microsoft azure", "azure devops"],
        "gcp": ["gcp", "google cloud", "google cloud platform", "gcloud"],
        "cloud architecture": ["cloud architecture", "cloud infrastructure"],
        "cloudformation": ["cloudformation", "aws cloudformation"],
        "cfn": ["cfn", "cloudformation"],
        "terraform": ["terraform", "tf", "terraform cloud"],
        "cloud functions": ["cloud functions", "lambda", "azure functions", "cloud run"],
        "api gateway": ["api gateway", "apigateway", "aws api gateway"],
        "s3": ["s3", "aws s3", "cloud storage"],
        "ec2": ["ec2", "virtual machines", "cloud compute"],
        "rds": ["rds", "managed database", "cloud database"],
        "cloudwatch": ["cloudwatch", "monitoring", "observability"],
        "vpc": ["vpc", "virtual private cloud", "networking"],
        "cloud security": ["cloud security", "iam", "cloud iam"],
    },
    "devops": {
        "docker": ["docker", "dockerfile", "docker compose", "containerization"],
        "kubernetes": ["kubernetes", "k8s", "helm", "istio", "kong"],
        "jenkins": ["jenkins", "ci/cd pipeline"],
        "gitlab ci": ["gitlab ci", "gitlab ci/cd", ".gitlab-ci.yml"],
        "github actions": ["github actions", "gh actions", "gha"],
        "ci/cd": ["ci/cd", "continuous integration", "continuous deployment", "continuous delivery"],
        "ansible": ["ansible"],
        "puppet": ["puppet"],
        "chef": ["chef"],
        "prometheus": ["prometheus"],
        "grafana": ["grafana"],
        "splunk": ["splunk"],
        "opentelemetry": ["opentelemetry", "otel", "jaeger", "zipkin"],
        "sre": ["sre", "site reliability engineering"],
        "devops": ["devops", "dev ops", "platform engineering"],
        "linux": ["linux", "ubuntu", "centos", "red hat", "rhel", "debian"],
        "nginx": ["nginx", "apache", "haproxy", "traefik"],
        "git": ["git", "github", "gitlab", "bitbucket", "version control"],
        "infrastructure as code": ["infrastructure as code", "iac", "terraform", "cloudformation"],
        "monitoring": ["monitoring", "alerting", "observability", "datadog", "new relic"],
        "secrets management": ["secrets management", "vault", "aws secrets manager"],
        "service mesh": ["service mesh", "istio", "consul", "linkerd"],
    },
    "mobile": {
        "react native": ["react native", "rn"],
        "flutter": ["flutter", "dart"],
        "android": ["android", "kotlin android", "java android"],
        "ios": ["ios", "swift ios", "objective-c"],
        "xamarin": ["xamarin", "xamarin.forms"],
        "ionic": ["ionic"],
        "kotlin multiplatform": ["kotlin multiplatform", "kmp"],
        "swiftui": ["swiftui"],
        "jetpack compose": ["jetpack compose"],
    },
    "security": {
        "cybersecurity": ["cybersecurity", "cyber security", "information security"],
        "penetration testing": ["penetration testing", "pen testing", "ethical hacking"],
        "siem": ["siem", "security information and event management"],
        "iam": ["iam", "identity and access management", "okta", "auth0", "saml", "oauth", "sso"],
        "iso 27001": ["iso 27001", "iso27001"],
        "soc": ["soc", "soc2", "soc 2", "security operations center"],
        "compliance": ["compliance", "regulatory compliance", "gdpr", "hipaa", "pci dss"],
        "grc": ["grc", "governance risk compliance"],
        "vulnerability": ["vulnerability", "vulnerability assessment", "vulnerability management", "nessus", "qualys"],
        "zero trust": ["zero trust", "zero trust architecture"],
        "encryption": ["encryption", "tls", "ssl", "pki"],
        "firewall": ["firewall", "network security", "waf"],
        "incident response": ["incident response", "forensics", "digital forensics"],
        "threat modeling": ["threat modeling", "threat intelligence"],
    },
    "qa_testing": {
        "qa": ["qa", "quality assurance", "testing"],
        "selenium": ["selenium", "selenium webdriver"],
        "cypress": ["cypress"],
        "playwright": ["playwright"],
        "junit": ["junit", "junit5", "junit 5"],
        "pytest": ["pytest", "python testing"],
        "test automation": ["test automation", "automation testing", "automated testing"],
        "manual testing": ["manual testing"],
        "postman": ["postman", "api testing"],
        "jmeter": ["jmeter", "performance testing"],
        "load testing": ["load testing", "stress testing", "performance testing"],
        "tdd": ["tdd", "test-driven development"],
        "bdd": ["bdd", "behavior-driven development", "cucumber"],
        "sonarqube": ["sonarqube", "sonar"],
    },
    "project_management": {
        "agile": ["agile", "agile methodology", "agile methodologies"],
        "scrum": ["scrum", "scrum master"],
        "kanban": ["kanban"],
        "product management": ["product management", "product owner", "product strategy"],
        "stakeholder management": ["stakeholder management"],
        "pmp": ["pmp", "project management professional"],
        "safe": ["safe", "scaled agile framework"],
        "jira": ["jira", "atlassian jira"],
        "confluence": ["confluence", "atlassian confluence"],
        "asana": ["asana"],
        "trello": ["trello"],
        "monday.com": ["monday.com", "monday"],
        "linear": ["linear"],
        "notion": ["notion"],
    },
    "business_tools": {
        "servicenow": ["servicenow", "service now"],
        "sap": ["sap", "sap erp", "sap s/4hana"],
        "salesforce": ["salesforce", "sf", "sfcc", "salesforce crm"],
        "workday": ["workday"],
        "hubspot": ["hubspot", "hub spot"],
        "zoho": ["zoho", "zoho crm"],
        "netsuite": ["netsuite", "oracle netsuite"],
        "dynamics 365": ["dynamics 365", "dynamics365", "microsoft dynamics"],
    },
    "erp_mainframe": {
        "mainframe": ["mainframe", "mainframes"],
        "cobol": ["cobol"],
        "sas": ["sas", "sas programming"],
        "abap": ["abap", "sap abap"],
        "pl/sql": ["pl/sql", "plsql", "oracle plsql"],
        "tibco": ["tibco", "tibco bw"],
        "mulesoft": ["mulesoft"],
        "dell boomi": ["dell boomi", "boomi"],
    },
    "healthcare": {
        "epic": ["epic", "epic systems", "epic emr"],
        "cerner": ["cerner", "oracle health"],
        "hl7": ["hl7", "fhir", "hl7 fhir"],
        "ehr": ["ehr", "emr", "electronic health record"],
        "clinical informatics": ["clinical informatics", "health informatics"],
        "hipaa": ["hipaa", "healthcare compliance"],
        "medical coding": ["medical coding", "icd-10", "cpt", "hcpcs"],
        "telemedicine": ["telemedicine", "telehealth"],
        "biomedical engineering": ["biomedical engineering", "biomedical"],
    },
    "finance": {
        "fintech": ["fintech", "financial technology"],
        "blockchain": ["blockchain", "web3", "ethereum", "solidity", "smart contracts", "defi"],
        "trading systems": ["trading systems", "algorithmic trading", "quantitative trading"],
        "risk management": ["risk management", "credit risk", "market risk"],
        "regulatory reporting": ["regulatory reporting", "basel", "mifid"],
        "payments": ["payments", "payment processing", "upi", "ach", "wire"],
    },
    "soft_skills": {
        "leadership": ["leadership", "team lead", "management"],
        "communication": ["communication", "verbal communication", "written communication"],
        "problem solving": ["problem solving", "analytical thinking", "critical thinking"],
        "teamwork": ["teamwork", "collaboration"],
        "adaptability": ["adaptability", "flexibility"],
        "time management": ["time management", "prioritization"],
    },
}


# ---------------------------------------------------------------------------
# Flatten to canonical → [synonyms] lookup
# ---------------------------------------------------------------------------

_SYNONYM_MAP: dict[str, str] = {}
_ALL_SKILLS: list[str] = []

for _cat, _skills in SKILLS_TAXONOMY.items():
    for canonical, synonyms in _skills.items():
        _ALL_SKILLS.append(canonical)
        for syn in synonyms:
            _SYNONYM_MAP[syn.lower().strip()] = canonical.lower().strip()


def normalize_skill(raw: str) -> str:
    """Map a raw skill string to its canonical form."""
    key = raw.lower().strip()
    return _SYNONYM_MAP.get(key, key)


def normalize_skills(raw_skills: list[str]) -> list[str]:
    """Deduplicate and normalize a list of skills."""
    seen: set[str] = set()
    result: list[str] = []
    for s in raw_skills:
        canonical = normalize_skill(s)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def find_skills_in_text(text: str) -> list[str]:
    """Find all known skills in a text blob (case-insensitive)."""
    text_lower = text.lower()
    found: list[str] = []
    seen: set[str] = set()
    for _cat, _skills in SKILLS_TAXONOMY.items():
        for canonical, synonyms in _skills.items():
            if canonical in seen:
                continue
            for syn in synonyms:
                pattern = r"\b" + re.escape(syn) + r"\b"
                if re.search(pattern, text_lower):
                    seen.add(canonical)
                    found.append(canonical)
                    break
    return found


def skill_similarity(skills_a: list[str], skills_b: list[str]) -> float:
    """Compute Jaccard similarity between two skill sets (0..1)."""
    set_a = {normalize_skill(s) for s in skills_a}
    set_b = {normalize_skill(s) for s in skills_b}
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def get_skills_by_category() -> dict[str, list[str]]:
    """Return {category: [canonical_skill, ...]}."""
    return {cat: list(skills.keys()) for cat, skills in SKILLS_TAXONOMY.items()}


def get_all_skills() -> list[str]:
    """Return flat sorted list of all canonical skills."""
    return sorted(set(_ALL_SKILLS))


def skill_gap(required: list[str], candidate: list[str]) -> dict[str, list[str]]:
    """Return skills that are required but missing from candidate."""
    req_set = {normalize_skill(s) for s in required}
    cand_set = {normalize_skill(s) for s in candidate}
    missing = sorted(req_set - cand_set)
    matched = sorted(req_set & cand_set)
    return {"missing": missing, "matched": matched}
