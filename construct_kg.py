
import os
import re
import spacy
from neo4j import GraphDatabase
from dotenv import load_dotenv
from urllib.parse import urlparse

# --- Load Environment Variables ---
load_dotenv()

# --- Neo4j Connection Details ---
# Parse the DSN from the .env file
neo4j_dsn = os.getenv("NEO4J_DSN")
if not neo4j_dsn:
    raise ValueError("NEO4J_DSN environment variable not set.")

parsed_dsn = urlparse(neo4j_dsn)
NEO4J_URI = f"{parsed_dsn.scheme}://{parsed_dsn.hostname}:{parsed_dsn.port}"
NEO4J_USER = parsed_dsn.username
NEO4J_PASSWORD = parsed_dsn.password


# --- spaCy Model ---
# to download it run once: python3 -m spacy download en_core_web_sm
nlp = spacy.load("en_core_web_sm")

# --- Directory containing the text files ---
TEXT_FILES_DIR = "/home/mz/k/KB/text-kb/"

def extract_participants_and_roles(text, driver):
    """
    Extracts participants and their roles from the text and creates nodes in Neo4j.
    """
    print("\n--- Extracting Participants and Roles ---")
    participant_matches = re.findall(r"([A-Z][a-zA-Z\s]+, [a-zA-Z\s&,]+):", text)

    participants = []
    for match in participant_matches:
        parts = match.split(',', 1)
        if len(parts) == 2:
            name = parts[0].strip()
            role_text = parts[1].strip()
            company = "Alphabet"  # Default
            if "Google" in role_text:
                company = "Google"
            if not any(p['name'] == name for p in participants):
                participants.append({'name': name, 'role': role_text, 'company': company})

    with driver.session() as session:
        for p in participants:
            print(f"Creating nodes for: {p['name']}, {p['role']}, {p['company']}")
            session.run("""
                MERGE (person:Person {name: $name})
                MERGE (company:Company {name: $company})
                MERGE (role:Role {title: $role})
                MERGE (person)-[:HAS_ROLE]->(role)
                MERGE (role)-[:WORKS_FOR]->(company)
                """, name=p['name'], role=p['role'], company=p['company'])

def extract_analysts_and_firms(text, driver):
    """
    Extracts analysts and their firms from the Q&A text and creates nodes in Neo4j.
    """
    print("\n--- Extracting Analysts and Firms ---")
    analyst_matches = re.findall(r"from ([A-Z][a-zA-Z\s]+) from ([A-Za-z\s&'’.-]+)\.", text)
    analyst_question_matches = re.findall(r"\n([A-Z][a-zA-Z\s]+), ([A-Za-z\s&'’.-]+):", text)

    analysts = {}
    for match in analyst_matches:
        name, firm = match[0].strip(), match[1].strip()
        if name not in analysts:
            analysts[name] = firm

    for match in analyst_question_matches:
        name, firm = match[0].strip(), match[1].strip()
        if 'ceo' not in firm.lower() and 'cfo' not in firm.lower() and 'svp' not in firm.lower():
            if name not in analysts:
                analysts[name] = firm

    with driver.session() as session:
        for name, firm in analysts.items():
            print(f"Creating nodes for Analyst: {name}, Firm: {firm}")
            session.run("""
                MERGE (analyst:Analyst {name: $name})
                MERGE (firm:Firm {name: $firm})
                MERGE (analyst)-[:REPRESENTS]->(firm)
                """, name=name, firm=firm)

def extract_financial_metrics(text, driver, speaker_name):
    """
    Extracts financial metrics from the text and creates nodes and relationships in Neo4j.
    """
    print(f"\n--- Extracting Financial Metrics for {speaker_name} ---")
    metric_matches = re.findall(r"([A-Z][a-zA-Z\s]+?)\s(?:was|were)\s(\$[\d\.]+\s\w+)", text)

    with driver.session() as session:
        for match in metric_matches:
            metric_name = match[0].strip()
            value_str = match[1].strip()
            
            parts = value_str.split()
            value = parts[0]
            unit = parts[1] if len(parts) > 1 else ""

            print(f"Creating FinancialMetric: {metric_name}, Value: {value}, Unit: {unit}")
            session.run("""
                MERGE (m:FinancialMetric {name: $name, value: $value, unit: $unit})
                """, name=metric_name, value=value, unit=unit)

            print(f"Creating relationship: ({speaker_name})-[:ANNOUNCES_METRIC]->({metric_name})")
            session.run("""
                MATCH (p:Person {name: $speaker_name})
                MATCH (m:FinancialMetric {name: $name})
                MERGE (p)-[:ANNOUNCES_METRIC]->(m)
                """, speaker_name=speaker_name, name=metric_name)

def extract_questions_and_answers(qa_text, driver):
    """
    Extracts questions and answers from the Q&A text and creates nodes and relationships in Neo4j.
    """
    print("\n--- Extracting Questions and Answers ---")
    with driver.session() as session:
        analysts = [record["name"] for record in session.run("MATCH (a:Analyst) RETURN a.name AS name")]
        executives = [record["name"] for record in session.run("MATCH (p:Person) RETURN p.name AS name")]

    qa_speakers = list(re.finditer(r"([A-Z][a-zA-Z\s]+, [a-zA-Z\s&,]+):", qa_text))
    last_question_text = None

    for i, speaker_match in enumerate(qa_speakers):
        speaker_full_name = speaker_match.group(1)
        speaker_name = speaker_full_name.split(',')[0].strip()

        start_pos = speaker_match.end()
        end_pos = qa_speakers[i + 1].start() if i + 1 < len(qa_speakers) else len(qa_text)
        speech_text = qa_text[start_pos:end_pos].strip()

        with driver.session() as session:
            if speaker_name in analysts:
                print(f"Creating Question node for: {speaker_name}")
                session.run("""
                    MERGE (q:Question {text: $text, asked_by: $speaker})
                    """, text=speech_text, speaker=speaker_name)
                last_question_text = speech_text

            elif speaker_name in executives and last_question_text:
                print(f"Creating Answer node for: {speaker_name}")
                session.run("""
                    MERGE (a:Answer {text: $text, answered_by: $speaker})
                    """, text=speech_text, speaker=speaker_name)

                print(f"Linking Answer to previous Question")
                session.run("""
                    MATCH (q:Question {text: $q_text})
                    MATCH (a:Answer {text: $a_text})
                    MERGE (q)-[:RECEIVES_ANSWER_FROM]->(a)
                    """, q_text=last_question_text, a_text=speech_text)

def extract_named_entities(text, driver):
    """
    Extracts named entities (Products, Services, Segments, Projects) from the text
    and creates corresponding nodes and relationships in Neo4j.
    """
    print("\n--- Extracting Named Entities (Products, Segments, Projects) ---")

    known_products = ["Google Search", "YouTube", "Chrome", "Chrome OS", "Android", "Google Play", "Pixel 6", "Google Meet", "Google Docs", "Google Sheets", "Google Slides", "Gmail", "Google Pay", "Google Analytics", "Search", "Maps"]
    known_segments = ["Google Cloud", "Other Bets", "Google Services", "Cloud"]
    known_projects = ["Waymo", "Wing", "Mandiant", "Performance Max", "Shorts", "smart canvas", "multisearch", "ATT", "DMA"]

    doc = nlp(text)
    extracted_entities = set()

    for ent in doc.ents:
        entity_text = ent.text.strip()
        entity_label = ""
        company = "Google"

        if entity_text in known_products:
            entity_label = "ProductOrService"
            if entity_text in ["YouTube", "Waymo", "Wing"]:
                 company = "Alphabet"
        elif entity_text in known_segments:
            entity_label = "Segment"
            if entity_text == "Other Bets":
                company = "Alphabet"
        elif entity_text in known_projects:
            entity_label = "ProjectOrInitiative"
            if entity_text in ["Waymo", "Wing", "Mandiant"]:
                company = "Alphabet"

        if entity_label and entity_text not in extracted_entities:
            print(f"Creating node for {entity_label}: {entity_text}, associated with {company}")
            with driver.session() as session:
                session.run(f"""
                    MERGE (e:{entity_label} {{name: $name}})
                    MERGE (c:Company {{name: $company}})
                    MERGE (e)-[:ASSOCIATED_WITH_COMPANY]->(c)
                    """, name=entity_text, company=company)
            extracted_entities.add(entity_text)

def process_file(file_path, driver):
    """
    Processes a single text file to extract entities and relationships
    and load them into the Neo4j database.
    """
    print(f"Processing file: {file_path}")

    with open(file_path, 'r') as f:
        text = f.read()

    qa_match = re.search(r"(Operator: Thank you. As a reminder, to ask a question.*)", text, re.DOTALL)
    if qa_match:
        qa_section = qa_match.group(1)
        remarks_text = text[:qa_match.start()]
    else:
        remarks_text = text
        qa_section = ""

    extract_participants_and_roles(remarks_text, driver)
    if qa_section:
        extract_analysts_and_firms(qa_section, driver)
        extract_questions_and_answers(qa_section, driver)
    
    print("\n--- Finding speakers and the metrics they announced ---")
    speaker_intros = list(re.finditer(r"([A-Z][a-zA-Z\s]+, [a-zA-Z\s&,]+):", remarks_text))

    for i, intro_match in enumerate(speaker_intros):
        speaker_name_full = intro_match.group(1)
        speaker_name = speaker_name_full.split(',')[0].strip()

        start_pos = intro_match.end()
        end_pos = speaker_intros[i + 1].start() if i + 1 < len(speaker_intros) else len(remarks_text)
        speech_text = remarks_text[start_pos:end_pos]

        extract_financial_metrics(speech_text, driver, speaker_name)

    extract_named_entities(text, driver)

def main():
    """
    Main function to connect to Neo4j and process all text files.
    """
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print("Successfully connected to Neo4j.")

        with driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:Role) REQUIRE r.title IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Analyst) REQUIRE a.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:Firm) REQUIRE f.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (m:FinancialMetric) REQUIRE m.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (q:Question) REQUIRE q.text IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Answer) REQUIRE a.text IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (ps:ProductOrService) REQUIRE ps.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Segment) REQUIRE s.name IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (pi:ProjectOrInitiative) REQUIRE pi.name IS UNIQUE")

        for filename in os.listdir(TEXT_FILES_DIR):
            if filename.endswith(".md"):
                file_path = os.path.join(TEXT_FILES_DIR, filename)
                process_file(file_path, driver)
                # Remove the break to process all files
                #break

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if driver:
            driver.close()
            print("Neo4j connection closed.")

if __name__ == "__main__":
    main()
