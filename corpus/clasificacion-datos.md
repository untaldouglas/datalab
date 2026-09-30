---
title: Clasificación de Servicios de Datos
source: Política de gobierno de datos sintética
date: 2026-02-10
classification: Internal
audience: Rectoría, Decanatos, VR Financiera, VR Académica
---

# Clasificación de Servicios de Datos

Todo activo de datos del lakehouse universitario lleva una única etiqueta de sensibilidad de la taxonomía `UniversityClassification`:

## Niveles

1. **Internal:** información de operación interna que puede mostrarse a audiencias institucionales. Los resúmenes agregados de los espacios de oro (`Gold_*`) son `Internal`.
2. **Confidential:** información restringida a roles específicos. Las capas de reglas de negocio (espacio `Silver`) son `Confidential` porque conservan identificadores técnicos.
3. **Restricted:** datos personales o sensibles. Las fuentes transaccionales son `Restricted` para consumo analítico.

## Reglas de consumo

Los tableros y asistentes solo consumen datasets `Internal` de los espacios de oro. Las capas `Confidential` y `Restricted` son capas internas de cálculo y no se exponen a usuarios finales. El acceso externo se realiza únicamente por el gateway de consultas aprobadas.

## Metadatos

La clasificación del servicio orienta el consumo pero no sustituye los controles de acceso: el catálogo aporta contexto, no permisos.
