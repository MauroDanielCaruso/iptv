# IPTV maintenance helper

Este repo ahora incluye un mantenedor para canales críticos.

## Qué hace

`iptv_guardian.py` revisa diariamente estos canales objetivo:

- C5N
- Crónica TV
- Telefe
- El Trece (Canal 13)
- TN

Valida si los links actuales de `lista.m3u` responden como HLS (`.m3u8`).

Si un canal está caído, **solo** reemplaza con links que estén en `config.targets.json` dentro de `replacement_candidates` (fuentes aprobadas por vos).

## Uso

```bash
cd projects/iptv
python3 scripts/iptv_guardian.py --config config.targets.json
```

Solo reporta (no modifica playlist).

Para aplicar reemplazos automáticos:

```bash
python3 scripts/iptv_guardian.py --config config.targets.json --apply
```

## Archivos

- `config.targets.json`: objetivos, aliases y candidatos de reemplazo.
- `scripts/iptv_guardian.py`: checker + reemplazo.
- `reports/latest_report.json`
- `reports/latest_report.txt`
- `backups/`: copias de `lista.m3u` antes de cambios.

## Flujo diario recomendado

1) Sincronizar con lista AR de iptv-org (agrega faltantes y actualiza URLs por nombre):

```bash
python3 scripts/iptv_sync_from_iptvorg.py --apply
```

2) Reordenar/pinear canales populares al principio (sin borrar nada):

```bash
python3 scripts/iptv_pin_order.py --apply
```

3) Revisar estado UP/DOWN sin modificar la lista (solo reporte):

```bash
python3 scripts/iptv_disable_down.py
```

Esto deja:
- `lista.m3u` = mantiene TODOS los canales (incluidos caídos)
- `reports/down_report.txt` = diagnóstico de UP/DOWN para que cambies links manualmente

## Job diario (OpenClaw)

```bash
openclaw cron add \
  --name "iptv:daily-sync-pin-and-report" \
  --cron "15 9 * * *" \
  --tz "America/Buenos_Aires" \
  --session main \
  --system-event "En /root/.openclaw/workspace/projects/iptv ejecutar: python3 scripts/iptv_sync_from_iptvorg.py --apply && python3 scripts/iptv_pin_order.py --apply && python3 scripts/iptv_disable_down.py. Avisar resumen breve a Mauro con cantidad de DOWN."
```

> Nota: los canales DOWN no se borran de `lista.m3u`; solo se reportan en `reports/down_report.txt` para corregir URL cuando quieras.
