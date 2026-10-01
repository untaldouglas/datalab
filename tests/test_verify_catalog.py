import unittest

from scripts.verify_catalog import verify_airflow, verify_consumption, verify_inventory, verify_lineage


class CatalogVerificationTest(unittest.TestCase):
    def test_inventory_passes_when_all_expected_assets_have_owner_and_description(self):
        entities = {
            "services": [{"name": name} for name in ("Moodle_Postgres", "ERP_MSSQL", "SIS_MSSQL", "ERPNext_Postgres", "Dremio_Federation")],
            "databases": [{"fullyQualifiedName": name, "owner": {"name": "admin"}, "description": "documentado"} for name in ("Moodle_Postgres.moodle_db", "ERP_MSSQL.erpnext_db", "SIS_MSSQL.sis_db", "ERPNext_Postgres.erpnext_db", "Dremio_Federation.Dremio")],
            "schemas": [{"fullyQualifiedName": name, "owner": {"name": "admin"}, "description": "documentado"} for name in ("Moodle_Postgres.moodle_db.moodle", "ERP_MSSQL.erpnext_db.erp", "SIS_MSSQL.sis_db.sis", "ERPNext_Postgres.erpnext_db.erp", "Dremio_Federation.Dremio.University_Lab", "Dremio_Federation.Dremio.Silver", "Dremio_Federation.Dremio.Gold_Rectoria", "Dremio_Federation.Dremio.Gold_Decanatos", "Dremio_Federation.Dremio.Gold_VR_Financiera")],
            "tables": [{"fullyQualifiedName": f"source.table_{index}", "owner": {"name": "admin"}, "description": "documentado"} for index in range(20)] + [{"fullyQualifiedName": fqn, "owner": {"name": "admin"}, "description": "documentado"} for fqn in ("Dremio_Federation.Dremio.University_Lab.Student_360", "Dremio_Federation.Dremio.Silver.Eligible_Student_Activity", "Dremio_Federation.Dremio.Silver.Academic_Activity_Events", "Dremio_Federation.Dremio.Silver.Demo_Reporting_Cutoff", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Academic_Summary", "Dremio_Federation.Dremio.Gold_Rectoria.Rectoral_Financial_Summary", "Dremio_Federation.Dremio.Gold_Decanatos.Decanato_Program_Participation", "Dremio_Federation.Dremio.Gold_VR_Financiera.Financial_Collection_Summary", "Dremio_Federation.Dremio.Gold_VR_Financiera.Monthly_Collection")],
            "dashboards": [{"fullyQualifiedName": f"Metabase_Institutional.{name}", "owner": {"name": "admin"}, "description": "documentado"} for name in ("Tablero_Rectoria", "Tablero_Decanatos", "Tablero_VR_Financiera")],
            "searchIndexes": [{"fullyQualifiedName": "Corpus_Search.corpus_chunks", "owner": {"name": "admin"}, "description": "documentado"}],
            "containers": [{"fullyQualifiedName": "Corpus_Storage.openrag_docs_corpus", "owner": {"name": "admin"}, "description": "documentado"}],
            "glossaryTerms": [{"fullyQualifiedName": f"Universidad.{name}", "owner": {"name": "admin"}, "description": "documentado"} for name in ("metrica_institucional", "fecha_de_corte", "ventana_de_participacion", "corte_financiero", "estudiante_elegible", "elegibilidad_temporal", "semestre_academico", "facultad", "programa_formativo", "servicio_formativo", "cobertura_de_integracion", "participacion_academica", "tasa_de_cobro", "cobros_por_periodo")],
            "domains": [{"fullyQualifiedName": name, "owner": {"name": "admin"}, "description": "documentado"} for name in ("Rectoria", "VR_Academica", "VR_Financiera", "Decanatos")],
            "pipelines": [{"fullyQualifiedName": f"Airflow_Ingestion.{name}", "owner": {"name": "admin"}, "description": "documentado"} for name in ("Moodle_Postgres_metadata", "ERP_MSSQL_metadata", "SIS_MSSQL_metadata", "ERPNext_Postgres_metadata", "Dremio_Federation_lineage", "Dremio_Federation_usage")],
            "charts": [{"fullyQualifiedName": f"Metabase_Institutional.{name}", "owner": {"name": "admin"}, "description": "documentado"} for name in ("Chart_Participacion_Facultad", "Chart_Estado_Financiero_Semestre", "Chart_Participacion_Programa", "Chart_Financiero_Semestre_VR", "Chart_Cobros_Mes")],
        }

        results = verify_inventory(entities)
        results.append(verify_consumption(entities))
        self.assertEqual(["PASS", "PASS", "PASS", "PASS"], [result["status"] for result in results])

    def test_inventory_fails_when_a_required_database_is_absent(self):
        results = verify_inventory({"services": [], "databases": [], "schemas": [], "tables": []})

        self.assertEqual("FAIL", results[0]["status"])

    def test_operational_checks_accept_erpnext_dq_and_lineage_nodes(self):
        dags = {"Moodle_Postgres_metadata", "ERP_MSSQL_metadata", "SIS_MSSQL_metadata", "ERPNext_Postgres_metadata", "Moodle_Postgres_profiler", "ERP_MSSQL_profiler", "SIS_MSSQL_profiler", "ERPNext_Postgres_profiler", "Dremio_Federation_lineage", "Dremio_Federation_usage"}
        dags.update({f"source_{index}_dq" for index in range(20)})
        lineage = {"nodes": [{"fullyQualifiedName": name} for name in ("SIS_MSSQL.sis_db.sis.students", "SIS_MSSQL.sis_db.sis.enrollments", "Moodle_Postgres.moodle_db.moodle.users", "ERPNext_Postgres.erpnext_db.erp.student_invoices")]}

        self.assertEqual("PASS", verify_airflow(dags, {dag: "success" for dag in dags})["status"])
        self.assertEqual("PASS", verify_lineage(lineage)["status"])
