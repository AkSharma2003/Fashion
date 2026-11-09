# Backup and restore

All business data is in PostgreSQL. Redis holds nothing that needs a backup. Product images are in Cloudflare
R2 (turn on R2 object versioning or a bucket copy separately). TallyPrime keeps its own data; back it up with
Tally's own backup on the Tally server.

The repository does not ship a backup job; set one up with the commands below before going live.

## Nightly backup

On the server, as a cron job (e.g. 02:30 IST, after the nightly reconciliation):

```bash
#!/bin/sh
# /opt/wearverse/backup.sh
set -e
STAMP=$(date +%Y-%m-%d_%H%M)
cd /opt/wearverse
docker compose exec -T db pg_dump -U fashionos -d fashionos -Fc > /backups/wearverse_$STAMP.dump
find /backups -name 'wearverse_*.dump' -mtime +30 -delete      # keep 30 days
# copy off the server, e.g.: rclone copy /backups r2:wearverse-backups
```

```cron
30 2 * * * /opt/wearverse/backup.sh >> /var/log/wearverse-backup.log 2>&1
```

Keep at least one copy **off the server** (another bucket or region). Use the user and database names from
your `DATABASE_URL` if you changed them.

## Restore

1. Stop writers: `docker compose stop api worker`.
2. Restore into a fresh database:
   ```bash
   docker compose exec -T db dropdb -U fashionos fashionos
   docker compose exec -T db createdb -U fashionos fashionos
   docker compose exec -T db pg_restore -U fashionos -d fashionos --no-owner < /backups/wearverse_<stamp>.dump
   ```
3. `docker compose start api worker` (the API runs `alembic upgrade head` on start).
4. Run the khata integrity check: `GET /api/v1/khata/integrity` should report no differences.
5. POS devices that billed offline after the backup time still hold those bills; they sync again because each
   bill's idempotency key is new to the restored database. Check Bills for the gap period.
6. Tally: vouchers sent to Tally after the backup time may be sent again when those bills sync back. Before
   starting the worker, list Tally vouchers with a `WV-` reference made after the backup time and compare them
   with Tally → Reconciliation the next morning; delete any duplicate in Tally. The bridge's Mode A read position
   (`tally_last_alter_id`) also goes back to the backup value, so vouchers made in Tally after the backup are read
   again; already-imported Tally GUIDs are skipped only if they are in the restored database, so check Bills for
   that period too.

## Test the restore

Once a month restore the latest backup into a scratch database (`createdb wearverse_restore_test`) and run the
integrity check against it. A backup that was never restored is not a backup.
