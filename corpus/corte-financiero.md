---
title: Corte Financiero y Semestre Académico
source: Definición institucional de métricas
date: 2026-02-01
classification: Internal
audience: VR Financiera, Rectoría
---

# Corte Financiero y Semestre Académico

## Corte financiero

El saldo pendiente o vencido se calcula al **corte financiero**. La emisión de cada factura se asigna al semestre académico según la **fecha de factura**. Los cobros se asignan según la **fecha real de pago** (`paid_at`), que es la fuente de verdad de la fecha de cobro según decisión institucional del 30 de septiembre de 2026.

## Semestre académico

El semestre impar va de enero a julio y el semestre par de agosto a diciembre. Una factura emitida en marzo de 2026 pertenece al semestre `2026-01`.

## Tasa de cobro

La tasa de cobro del semestre es el cociente entre el monto pagado y el monto facturado al corte. Se reporta junto con el saldo pendiente; no se interpreta como proyección de recaudación.

## Limitación histórica

La plataforma registra una foto del estado de las facturas a la fecha de carga. No reconstruye retrospectivamente el saldo de una fecha pasada porque no conserva el historial de cambios de estado.
