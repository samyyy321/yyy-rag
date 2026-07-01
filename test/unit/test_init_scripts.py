from scripts.init_medical_graph import initialize_medical_graph, load_graph_data
from scripts.init_operational_tables import initialize_operational_tables


class FakeConnection:
    """记录初始化脚本提交的 SQL 语句。"""

    def __init__(self):
        self.statements = []

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params))


class FakeSession:
    """在不连接 Neo4j 的情况下记录图谱写入语句。"""

    def __init__(self):
        self.statements = []

    def run(self, statement, **params):
        self.statements.append((statement, params))

    def execute_write(self, callback, payload):
        callback(self, payload)


class FakeSessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, *_args):
        return False


class FakeDriver:
    def __init__(self):
        self.session_instance = FakeSession()

    def session(self, **_kwargs):
        return FakeSessionContext(self.session_instance)


def test_initialize_operational_tables_creates_prompt_tables_and_demo_rows():
    """运营表脚本应创建 prompt 定义的五张表并写入幂等演示数据。"""
    connection = FakeConnection()

    initialize_operational_tables(connection)

    statements = [statement for statement, _ in connection.statements]
    for table_name in ("categories", "products", "customers", "orders", "order_items"):
        assert any(f"CREATE TABLE IF NOT EXISTS {table_name}" in item for item in statements)
    assert any("INSERT INTO categories" in item for item in statements)
    assert any("INSERT INTO orders" in item for item in statements)


def test_initialize_medical_graph_creates_constraints_and_merges_demo_data():
    """图谱脚本应创建约束，并通过参数化 MERGE 写入演示节点和关系。"""
    driver = FakeDriver()
    graph_data = {
        "nodes": [
            {"label": "Disease", "name": "演示疾病", "properties": {"demo_only": True}},
            {"label": "Symptom", "name": "演示症状", "properties": {"demo_only": True}},
        ],
        "relationships": [
            {
                "from": {"label": "Disease", "name": "演示疾病"},
                "type": "HAS_SYMPTOM",
                "to": {"label": "Symptom", "name": "演示症状"},
            }
        ],
    }

    initialize_medical_graph(driver, graph_data, database="neo4j")

    statements = driver.session_instance.statements
    assert any("CREATE CONSTRAINT disease_name_unique" in statement for statement, _ in statements)
    node_statement, node_params = next(
        (statement, params) for statement, params in statements if "MERGE (node:Disease" in statement
    )
    assert "$name" in node_statement
    assert node_params["name"] == "演示疾病"
    relationship_statement, relationship_params = next(
        (statement, params)
        for statement, params in statements
        if "relationship:HAS_SYMPTOM" in statement
    )
    assert "MATCH (source:Disease {name: $source_name})" in relationship_statement
    assert "MATCH (target:Symptom {name: $target_name})" in relationship_statement
    assert relationship_params == {"source_name": "演示疾病", "target_name": "演示症状"}

def test_load_graph_data_accepts_utf8_bom_json(tmp_path):
    """PowerShell 写入带 BOM 的演示 JSON 时，图谱脚本仍应能加载。"""
    data_path = tmp_path / "graph.json"
    data_path.write_bytes(
        b"\xef\xbb\xbf" + b'{"disclaimer":"demo","nodes":[],"relationships":[]}'
    )

    graph_data = load_graph_data(data_path)

    assert graph_data["disclaimer"] == "demo"
