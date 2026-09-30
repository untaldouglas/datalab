---
title: Política de Cobranza de Matrícula
source: Política financiera sintética
date: 2026-02-25
classification: Confidential
audience: VR Financiera
---

# Política de Cobranza de Matrícula

## Estados de pago

El pago de matrícula registra cinco estados: `paid`, `partial`, `pending`, `overdue` y `cancelled`. Solo `paid` y `partial` habilitan para cursar.

## Registro de cobros

Cada pago registrado conserva la **fecha real de pago** (`paid_at`). Los pagos parciales registran el monto efectivamente recibido; el saldo restante permanece visible en la factura asociada.

## Seguimiento

Las facturas en estado `overdue` requieren seguimiento de cobranza. La cifra de saldo vencido del tablero financiero corresponde a facturas con ese estado al corte financiero.
