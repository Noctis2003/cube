import os
import re
from neo4j import GraphDatabase

URI = "neo4j://127.0.0.1:7687"
AUTH = ("neo4j", "Leonaidas5@123")  # update with your neo4j password
OUTPUT_DIR = "./cube_models"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Fetch tables, columns, and foreign key joins
QUERY = """
MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
OPTIONAL MATCH (c)-[:REFERENCES_FOREIGN_KEY]->(targetCol:Column)<-[:HAS_COLUMN]-(targetTable:Table)
RETURN 
    t.name AS tableName,
    t.fullyQualifiedName AS tableFqn,
    t.tableType AS tableType,
    collect(DISTINCT {
        name: c.name,
        type: c.dataType,
        constraint: c.constraint
    }) AS columns,
    collect(DISTINCT {
        sourceCol: c.name,
        targetTable: targetTable.name,
        targetCol: targetCol.name
    }) AS joins
"""

def map_column_type(data_type):
    dt = str(data_type).lower()
    if "int" in dt or "numeric" in dt or "float" in dt or "double" in dt or "decimal" in dt:
        return "number"
    if "date" in dt or "timestamp" in dt or "time" in dt:
        return "time"
    if "bool" in dt:
        return "boolean"
    return "string"

def generate_cube_yaml(record):
    tbl_name = record["tableName"]
    tbl_fqn = record["tableFqn"]
    columns = record["columns"]
    joins = [j for j in record["joins"] if j["targetTable"] is not None]

    lines = [f"cubes:", f"  - name: {tbl_name}", f"    sql_table: {tbl_fqn}"]

    # Add Joins
    if joins:
        lines.append("    joins:")
        for j in joins:
            lines.append(f"      - name: {j['targetTable']}")
            lines.append(f"        sql: '{{CUBE}}.{j['sourceCol']} = {{{j['targetTable']}.{j['targetCol']}}}'")
            lines.append(f"        relationship: many_to_one")

    # Add Dimensions
    lines.append("    dimensions:")
    for col in columns:
        c_name = col["name"]
        c_type = map_column_type(col["type"])
        is_pk = col.get("constraint") == "PRIMARY_KEY"

        lines.append(f"      - name: {c_name}")
        lines.append(f"        sql: {c_name}")
        lines.append(f"        type: {c_type}")
        if is_pk:
            lines.append("        primary_key: true")

    # Add Measures
    lines.append("    measures:")
    lines.append("      - name: count")
    lines.append("        type: count")

    for col in columns:
        c_name = col["name"]
        c_type = map_column_type(col["type"])
        if c_type == "number" and col.get("constraint") != "PRIMARY_KEY":
            lines.append(f"      - name: total_{c_name}")
            lines.append(f"        type: sum")
            lines.append(f"        sql: {c_name}")
            lines.append(f"      - name: avg_{c_name}")
            lines.append(f"        type: avg")
            lines.append(f"        sql: {c_name}")

    return "\n".join(lines)

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    with driver.session() as session:
        result = session.run(QUERY)
        for record in result:
            cube_code = generate_cube_yaml(record)
            file_path = os.path.join(OUTPUT_DIR, f"{record['tableName']}.yml")
            with open(file_path, "w") as f:
                f.write(cube_code)
            print(f"Generated Cube model: {file_path}")