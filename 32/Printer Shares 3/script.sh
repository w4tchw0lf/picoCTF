#!/bin/bash
echo "Health Check: $(date)" >> /challenge/shares/cron.log
cat /challenge/secure-shares/flag.txt >> /challenge/shares/cron.log 2>&1
