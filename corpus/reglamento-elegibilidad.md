---
title: Reglamento de Elegibilidad para Cursar
source: Reglamento Académico Sintético UJMD
date: 2026-01-15
classification: Internal
audience: Rectoría, Decanatos
---

# Reglamento de Elegibilidad para Cursar

## Requisito general

Un estudiante está habilitado para cursar servicios formativos cuando su matrícula está vigente a la fecha de corte y su pago de matrícula está en estado `paid` o `partial`.

## Pago parcial

El estado `partial` concede una **elegibilidad temporal**: habilita para cursar mientras la matrícula permanezca vigente. No constituye pago definitivo ni elimina el saldo pendiente. La fecha de fin de gracia para completar el pago no está definida en esta POC; antes de producción debe ser establecida por la política financiera.

## Estados no habilitantes

Las matrículas con pago `unpaid` u `overdue`, o con registro distinto de `vigente`, no generan elegibilidad. Estos estudiantes no se incluyen en los agregados de participación institucional.

## Fecha de corte

Toda métrica de elegibilidad se calcula respecto a una **fecha de corte** explícita. En el laboratorio la fecha de corte demostrativa es el 31 de marzo de 2026 y se declara en la vista `Demo_Reporting_Cutoff`. Ningún indicador usa la fecha del servidor de forma implícita.
