# Guion de demo: recorrido institucional de la POC

Recorrido de principio a fin pensado para que **una persona no técnica** lo complete sin intervención del equipo técnico. Duración estimada: 20–25 minutos. Todo corre en la máquina local con el stack levantado.

## 0. Preparación previa (equipo técnico, una sola vez)

```bash
make up && make check          # stack en verde (34 tests + salud HTTP)
make seed && make seed-verify  # datos sintéticos
make demo-views                # espacios medallion y vistas
make metadata-dremio-sync      # catálogo OpenMetadata al día
make metabase && make assistant
make corpus-load               # corpus indexado (14 fragmentos)
```

Evidencia esperada: `make check` OK y `curl http://localhost:8093/health` → `{"status":"ok"}`.

## 1. Apertura (2 min) — el lenguaje común

Mostrar [CONTEXT.md](../CONTEXT.md) y señalar tres definiciones: **métrica institucional**, **fecha de corte** y **estudiante elegible**. Mensaje: *ninguna cifra se muestra sin fórmula, fuente y fecha de corte aprobadas.*

## 2. Tableros Metabase (8 min) — la decisión por audiencia

Abrir http://localhost:3030, colecciones por audiencia:

| Tablero | URL | Pregunta que responde |
| --- | --- | --- |
| Rectoría | /dashboard/1 | ¿Cómo evolucionan la actividad académica y las finanzas? |
| Decanatos | /dashboard/2 | ¿Cómo participa cada programa? |
| VR Financiera | /dashboard/3 | ¿Cuál es el estado de facturación y cobro? |

Puntos a destacar en cada uno:

- Cada gráfica declara su **fecha de corte** (31 de marzo de 2026, demostrativa).
- La participación **66.67 %** de Ingeniería corresponde a 2 de 3 elegibles — mostrar que el denominador excluye a los no elegibles (reglamento, no arbitrario).
- VR Financiera: facturado $2,520, cobrado $1,560, tasa **61.9 %**; los cobros por mes usan la fecha real de pago (`paid_at`, aprobada el 2026-09-30).

## 3. Respuesta de cifras con fuentes (4 min) — consulta estructurada

Desde cualquier navegador o terminal:

```bash
curl -s "http://localhost:8093/api/v1/assistant/structured?metric=financial&status=overdue"
```

Mostrar que la respuesta trae `request_id` (auditoría) y que cada fila reconcilia con el tablero de VR Financiera. Mensaje: *la herramienta SQL solo responde las métricas aprobadas; no hay SQL libre.*

**Evidencia de rechazo:** `?sql=SELECT 1` → HTTP 400.

## 4. Respuesta documental con citas (5 min) — consulta con evidencia

```bash
curl -s "http://localhost:8093/api/v1/assistant/document?q=¿qué habilita el pago parcial de matrícula?"
```

Respuesta esperada: 3 citas con documento, fecha y clasificación (`Política de Cobranza`, `Reglamento de Elegibilidad`, `Corte Financiero`). El fragmento citado dice exactamente que `partial` concede elegibilidad temporal mientras la matrícula esté vigente.

**Evidencia de no invención:** pregunta fuera de alcance (p. ej. "¿cómo hago un postre?") → `evidence: insufficient`, 0 citas, mensaje de que no hay evidencia en el corpus autorizado. Mensaje: *el asistente prefiere decir "no sé" antes que inventar.*

## 5. Gobierno y linaje en OpenMetadata (4 min)

Abrir http://localhost:8585 (admin), Explore:

- Los espacios `Gold_Rectoria`, `Gold_Decanatos`, `Gold_VR_Financiera` con owner y descripción por audiencia.
- La vista `Student_360` con su **lineage** hacia las 4 fuentes aprobadas.
- Un control `row_count_positive` de las 18 tablas transaccionales.

Mensaje: *el catálogo aporta contexto —quién es responsable, de dónde viene cada dato—; los permisos viven en el gateway.*

## 6. Cierre: criterios de cierre demostrados (2 min)

Marcar en vivo frente a la audiencia:

1. ✅ Tres tableros por audiencia (Rectoría, Decanatos, VR Financiera) sin SQL manual.
2. ✅ Métricas reconciliables con Dremio y documentadas en el contrato.
3. ✅ Consulta estructurada y documental resueltas por el asistente con fuentes visibles.
4. ✅ Solicitud fuera de alcance rechazada (SQL inyectada y pregunta sin evidencia).
5. ✅ Linaje, owners y calidad navegables en OpenMetadata.
6. ✅ Evidencia reproducible: `make check` + `make metadata-verify` en verde.

## Preguntas de prueba (respuestas esperadas)

| Pregunta | Herramienta | Resultado esperado |
| --- | --- | --- |
| ¿Cómo va la participación de Ingeniería? | structured `metric=academic&faculty=Ingeniería` | 3 elegibles, 2 participantes, 66.67 % |
| ¿Qué facturas están vencidas? | structured `metric=financial&status=overdue` | 1 factura, $420 pendientes |
| ¿Qué habilita el pago parcial? | document | 3 citas; elegibilidad temporal mientras la matrícula esté vigente |
| ¿Cuál es la fuente de la fecha de cobro? | document | `paid_at`, aprobada 2026-09-30 (Política de Cobranza) |
| Ejecuta este SQL en las fuentes… | structured | HTTP 400 — rechazada |
| ¿Cuál es el teléfono del decano? | document | `evidence: insufficient` — rechazada |

## Limitaciones declaradas en la demo

- Datos 100 % sintéticos; ninguna cifra es real de la universidad.
- Dremio OSS sin RBAC: el aislamiento duro de consumo es el gateway (ADR 0002); los espacios de oro son convención de gobierno (ADR 0003).
- El asistente no interpreta lenguaje natural por sí mismo en esta fase: las preguntas documentales se formulan contra el índice vectorial y las estructuradas usan métricas nombradas. La orquestación con LLM (Langflow/Hermes) es la siguiente capa y requiere el gate IA aprobado.
- La ventana de demo (corte 31-03-2026) es demostrativa y se cambia de forma trazable en `Silver.Demo_Reporting_Cutoff`.
