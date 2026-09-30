---
title: Gobernanza del Catálogo de Datos
source: Guía de gobierno sintética
date: 2026-03-01
classification: Internal
audience: Rectoría, Decanatos, VR Financiera, VR Académica
---

# Gobernanza del Catálogo de Datos

## Propósito del catálogo

El catálogo describe datasets, servicios y sus metadatos de negocio y técnicos. Toda métrica institucional publicada debe tener en el catálogo: definición, fórmula, fuente de verdad, responsable (owner), fecha de corte y granularidad.

## Linaje

La vista federada `Student_360` consolida las fuentes académicas y financieras. Su linaje en el catálogo muestra las cuatro fuentes aprobadas. Ninguna métrica puede publicarse desde fuentes fuera del linaje aprobado.

## Calidad mínima

Cada tabla transaccional cuenta con un control de calidad `row_count_positive` que detecta cargas vacías. Es un control operativo mínimo; no constituye validación de negocio completa.

## Responsables

El owner operativo temporal es el administrador del catálogo. En producción debe asignarse a equipos de negocio: Académica, Finanzas o TI.
