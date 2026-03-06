#!/bin/bash
# Start SQL Server in the background, wait for it, run init.sql, then keep running.
set -e

/opt/mssql/bin/sqlservr &
SQL_PID=$!

echo "Waiting for SQL Server to be ready..."
for i in $(seq 1 60); do
    /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
        -Q "SELECT 1" > /dev/null 2>&1 && break
    sleep 2
done

echo "Running init.sql..."
/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
    -b -V 16 -r 1 -i /sql/init.sql

echo "Database initialized."
wait $SQL_PID
