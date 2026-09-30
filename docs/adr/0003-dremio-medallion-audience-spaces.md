# ADR 0003: Arquitectura medallion y espacios de oro por audiencia

**Estado: aceptada.**

## Contexto

Las vistas aprobadas vivían todas en el espacio plano `University_Lab`, mezclando dos niveles distintos: reglas de negocio (`Eligible_Student_Activity`, `Academic_Activity_Events`, `Demo_Reporting_Cutoff`) y agregados de consumo (`Rectoral_Academic_Summary`, `Rectoral_Financial_Summary`). La frontera existía de facto pero era invisible: ninguna vista declaraba su capa, las reglas de negocio no eran reutilizables por futuras audiencias y Metabase no tendría un lugar claro donde apuntar.

## Decisión

Adoptar el patrón medallion con espacios Dremio:

- **Bronce:** las fuentes ya registradas (`Moodle_Postgres`, `SIS_MSSQL`, `ERPNext_Postgres`, `MinIO_Lakehouse`). No se crean objetos ni copias; bronce es la referencia a la fuente cruda.
- **Plata:** espacio `Silver`. Contiene las reglas de negocio reutilizables: `Eligible_Student_Activity`, `Academic_Activity_Events` y la dimensión `Demo_Reporting_Cutoff`. Ninguna audiencia consulta plata directamente.
- **Oro:** un espacio por audiencia según el plan de demo: `Gold_Rectoria`, `Gold_Decanatos`, `Gold_VR_Financiera`. Sólo aquí viven los agregados de consumo; Metabase y el gateway apuntan exclusivamente a oro.

`make demo-views` crea los espacios de forma idempotente, elimina las vistas heredadas de `University_Lab` y recrea las vistas en su capa correspondiente. El gateway (`metrics-gateway`) consulta `Gold_Rectoria`.

## Consecuencias

- Las reglas de negocio (elegibilidad, mapeo de facultad, ventana de participación) se mantienen en un solo lugar; nuevas audiencias reutilizan plata sin re-derivar lógica.
- OpenMetadata cataloga por espacio, lo que alinea inventario con audiencias.
- **Este patrón no aporta aislamiento de acceso en Dremio OSS:** sin RBAC, la separación es convención de gobierno y lineage. El control de acceso real sigue siendo el gateway de consulta aprobada (ADR 0002) y, más adelante, Dremio Enterprise/Cloud si se aprueba el gate correspondiente.
- `University_Lab` queda para el VDS federado `Student_360` y su lineage; las vistas de demo ya no se crean allí.
