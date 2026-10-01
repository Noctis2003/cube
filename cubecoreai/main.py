import json
import os
import requests
from google import genai
from google.genai import types

API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

CUBE_API_URL = "http://localhost:4000/cubejs-api/v1/load"
CUBE_META_URL = "http://localhost:4000/cubejs-api/v1/meta"

def get_cube_catalog() -> str:
    """Fetch active cubes, measures, and dimensions from Cube Core."""
    try:
        response = requests.get(CUBE_META_URL, timeout=5)
        if response.status_code == 200:
            meta = response.json()
            cubes_summary = []
            for c in meta.get("cubes", []):
                cube_name = c["name"]
                measures = [m["name"] for m in c.get("measures", [])]
                dimensions = [d["name"] for d in c.get("dimensions", [])]
                cubes_summary.append(
                    f"Cube: '{cube_name}'\n  - Measures: {measures}\n  - Dimensions: {dimensions}"
                )
            if cubes_summary:
                return "\n".join(cubes_summary)
    except Exception as e:
        print(f"Warning: Could not connect to Cube meta endpoint: {e}")

    # Fallback catalog based on your metadata tables
    return """
Cube: 'raw_customers'
  - Dimensions: ['raw_customers.customer_id', 'raw_customers.full_name', 'raw_customers.email', 'raw_customers.tier']
  - Measures: ['raw_customers.count']
Cube: 'raw_transactions'
  - Dimensions: ['raw_transactions.txn_id', 'raw_transactions.customer_id', 'raw_transactions.txn_date']
  - Measures: ['raw_transactions.count', 'raw_transactions.total_amount', 'raw_transactions.avg_amount']
"""

def generate_cube_query(user_prompt: str, catalog: str) -> dict:
    """Use Gemini to translate a plain English question into a Cube REST query JSON."""
    system_instruction = f"""
You are an expert BI analytics assistant that translates plain English business questions 
into Cube REST API query JSON objects.

You MUST choose dimensions and measures ONLY from the following schema catalog:
{catalog}

Rules:
1. Always prefix dimensions and measures with their cube name (e.g., 'raw_customers.tier', 'raw_transactions.total_amount').
2. Return ONLY a valid JSON object.
3. Do not include markdown code block formatting (like ```json), commentary, or extra text.

Valid JSON Structure:
{{
  "measures": ["<cube_name>.<measure_name>"],
  "dimensions": ["<cube_name>.<dimension_name>"],
  "order": {{"<cube_name>.<measure_name>": "desc"}},
  "limit": 50
}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text.strip())

def execute_cube_query(query_dict: dict) -> dict:
    """Send the structured JSON query to Cube Core."""
    headers = {"Content-Type": "application/json"}
    response = requests.post(CUBE_API_URL, headers=headers, json={"query": query_dict})
    return response.json()

def answer_with_data(user_prompt: str, data_result: list) -> str:
    """Use Gemini to summarize the returned database records."""
    prompt = f"""
The user asked: "{user_prompt}"

The semantic database returned these records:
{json.dumps(data_result, indent=2)}

Provide a clear, natural-language executive summary directly answering the user's question.
State the key numbers and insights clearly.
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text.strip()

def main():
    print("Fetching active semantic layer models from Cube Core...")
    catalog = get_cube_catalog()
    print("Catalog loaded.\n")

    while True:
        try:
            user_input = input("Enter your analytics question (or 'exit' to quit): ").strip()
            if not user_input or user_input.lower() in ("exit", "quit"):
                break

            print("\n[1/3] Generating Cube semantic query with Gemini...")
            cube_query = generate_cube_query(user_input, catalog)
            print(f"Generated Query:\n{json.dumps(cube_query, indent=2)}")

            print("\n[2/3] Executing query against Cube Core...")
            cube_response = execute_cube_query(cube_query)
            data_rows = cube_response.get("data", [])
            print(f"Retrieved {len(data_rows)} rows from database.")

            print("\n[3/3] Generating answer with Gemini...")
            answer = answer_with_data(user_input, data_rows)

            print("\n" + "=" * 50)
            print(f"ANSWER:\n{answer}")
            print("=" * 50 + "\n")

        except Exception as err:
            print(f"Error occurred: {err}\n")

if __name__ == "__main__":
    main()