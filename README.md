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

## Job diario (OpenClaw)

Ejemplo para correr todos los días 09:15 (Buenos Aires):

```bash
openclaw cron add \
  --name "iptv:guardian-daily" \
  --cron "15 9 * * *" \
  --tz "America/Buenos_Aires" \
  --session main \
  --system-event "Ejecutá en /root/.openclaw/workspace/projects/iptv: python3 scripts/iptv_guardian.py --config config.targets.json --apply. Si hay cambios, avisar resumen. Si no hay cambios, no enviar mensaje."
```

> Nota: este flujo no busca fuentes no autorizadas automáticamente; trabaja con tus candidatos aprobados.
