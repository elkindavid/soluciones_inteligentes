@echo off
sqlite3 local.db ".tables" ".headers on" ".mode column" "select * from users;"
pause
