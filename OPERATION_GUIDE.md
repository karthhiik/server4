# Barise Business Plan Module: Production Operation Guide

**Version:** 1.0  
**Date:** 2026-04-03  
**Module:** Business Plan Canvas (Tasks 1-32, 100% Complete)

---

## KEY METRICS TO MONITOR

### Application Performance
- Request Rate: 100-500 req/sec
- Response Time P95: < 500ms
- Error Rate: < 0.1%
- Success Rate: > 99.9%

### Business Plan Generation
- Average Generation Time: 30-90 seconds
- Completion Rate: > 99%
- Web Search Success: > 95%
- Multi-user Sync Latency: < 100ms

### Infrastructure
- CPU Usage: < 70%
- Memory Usage: < 80%
- Disk Usage: < 80%
- Network I/O: < 50% capacity

### Database
- Query Time P95: < 100ms
- Connection Pool Usage: < 80%
- Replication Lag: < 1 second

### WebSocket
- Active Connections: monitor trend
- Connection Success Rate: > 99%
- Message Latency: < 100ms
- Disconnection Rate: < 1%

---

## DAILY OPERATIONS CHECKLIST

### Morning Checks
- Check system health: curl https://api.yourdomain.com/health
- Verify database: mongo --eval "db.adminCommand('ping')"
- Check Redis: redis-cli ping
- Review error logs: tail -100 /var/log/fastapi.log | grep ERROR
- Monitor resources: free -h && df -h
- Verify backups: ls -lh /backups/daily/ | tail -5

### Hourly Monitoring (Business Hours)
- API response time
- Active WebSocket connections
- Cache hit rate
- Generation success rate
- Error rate

### Evening Tasks
- Generate daily report
- Archive logs
- Verify night backups scheduled
- Update incident log

---

## TROUBLESHOOTING

### WebSocket Connection Issues
1. Check logs: tail -f /var/log/fastapi.log | grep websocket
2. Verify endpoint health
3. Check Nginx WebSocket config
4. Test connectivity with wscat
5. Restart FastAPI service

### Slow Generation (>90 sec)
1. Check web search latency
2. Verify cache hit rate: redis-cli info stats
3. Check LLM API performance
4. Review database query times: mongo profiling
5. Check concurrent load: ps aux | grep business_plan

### High Memory Usage (>80%)
1. Identify process: top -n 1
2. Check Redis memory: redis-cli info memory
3. Monitor WebSocket connections: netstat -an
4. Clear cache if needed: redis-cli FLUSHDB
5. Restart services if critical: systemctl restart fastapi

### Database Connection Failures
1. Test MongoDB: mongo "mongodb+srv://<connection>"
2. Check connection pool: mongo --eval "db.currentOp()"
3. Verify network: ping <cluster-host>
4. Check firewall: sudo iptables -L
5. Restart FastAPI: systemctl restart fastapi

---

## BACKUP & RECOVERY

### Automated Backup Schedule
- Daily backup: 2 AM to /backups/daily/
- Weekly backup: Sunday 3 AM to /backups/weekly/
- Retention: 30 days daily, 52 weeks weekly

### Backup Verification (Weekly)
```bash
mongorestore --archive=/backups/daily/backup-latest.archive \
  --nsInclude='barise_test.*' --drop
mongo --eval "db.business_plans.countDocuments()"
```

### Full Recovery Procedure
```bash
mongorestore --archive=/backups/backup-latest.archive \
  --uri mongodb+srv://<connection> --drop
```

### Partial Recovery (Single Collection)
```bash
mongorestore --archive=/backups/backup-latest.archive \
  --uri mongodb+srv://<connection> \
  --nsInclude='barise_production.business_plans' --drop
```

---

## PERFORMANCE OPTIMIZATION

### Cache Hit Rate Monitoring
```bash
redis-cli info stats
# Target: hits / (hits + misses) > 80%
# Action: If <70%, analyze cache keys and TTLs
```

### Database Query Performance
```bash
# Enable slow query logging
mongo
> db.setProfilingLevel(1, { slowms: 100 })

# View slow queries
> db.system.profile.find({millis: {$gt: 100}})
>   .sort({ts: -1}).limit(10)

# Rebuild indexes if needed
> db.business_plans.reIndex()
```

### API Load Testing
```bash
# Apache Bench
ab -n 1000 -c 10 https://api.yourdomain.com/health

# wrk tool
wrk -t4 -c100 -d30s https://api.yourdomain.com/health
```

---

## PERFORMANCE TARGETS

- Uptime: 99.9%+
- API Response Time P95: <500ms
- Generation Time: 30-90 seconds
- WebSocket Latency: <100ms
- Database Query Time P95: <100ms
- Error Rate: <0.1%
- Cache Hit Rate: >80%

---

## ALERTS TO CONFIGURE

- API error rate > 0.1%
- Response time P95 > 500ms
- WebSocket disconnections > 10/min
- Memory usage > 80%
- CPU usage > 70%
- Disk usage > 80%
- Database replication lag > 5s
- Cache evictions > 100/min

---

## SECURITY OPERATIONS

### Weekly
- Check outdated packages: pip list --outdated
- Review error logs for security issues
- Verify SSL certificate validity

### Monthly
- Rotate API keys (every 90 days)
- Run security scans: npm audit, pip-audit
- Review access logs for anomalies

### Quarterly
- Contract external penetration testing
- Update security policies
- Conduct disaster recovery drill

---

## ESCALATION PATH

- CRITICAL (system down): Immediate - page on-call engineer
- HIGH (feature broken): <15 minutes - escalate to senior engineer
- MEDIUM (performance issue): <1 hour - escalate to engineering lead
- LOW (improvements): <1 day - create ticket for planning

---

## QUICK REFERENCE RUNBOOK

| Issue | Quick Fix | Owner | ETA |
|-------|-----------|-------|-----|
| High CPU | identify process, restart service | SRE | 15 min |
| Memory leak | ps aux, restart service | DevOps | 10 min |
| Slow queries | mongo profile, rebuild index | DBA | 30 min |
| Disk full | du -sh, archive logs | SysAdmin | 20 min |
| WebSocket down | systemctl restart fastapi | SRE | 5 min |
| Cache stale | redis-cli FLUSHDB ASYNC | DBA | 5 min |
| DB connection fail | verify URI, restart fastapi | DevOps | 10 min |

---

**Status:** Production Ready  
**Updated:** 2026-04-03  
**Approved By:** Operations Team  
**Last Drill:** Initial Deploy  
**Next Review:** 2026-05-03
